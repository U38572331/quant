import pandas as pd
import numpy as np
import databento as db
import plotly.graph_objects as go
import os
from datetime import time

# --- Config ---
RESULTS_CSV = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\vwap_retest_raw_results.csv"
DATA_FILE = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUT_HTML = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\visualize_vwap_trades.html"

print("Loading raw trades...")
res = pd.read_csv(RESULTS_CSV)
# Lock onto the optimal TP_Size=0.8
res_08 = res[res['TP_Size'] == 0.8].copy()
# Identify top 20 recent trade dates
target_dates = res_08['Date'].unique()[-20:]
target_res = res_08[res_08['Date'].isin(target_dates)]

print(f"Loading tick data for {len(target_dates)} specific dates (may take a moment)...")
store = db.DBNStore.from_file(DATA_FILE)
df = store.to_df()
df = df[df['symbol'].astype(str).str.match(r'^NQ[HMUZ]\d$')]

df.index = pd.to_datetime(df.index).tz_convert('US/Eastern')
df['date'] = df.index.date

# Filter globally first to save massive memory and time
df = df[df['date'].isin(pd.to_datetime(target_dates).date)].copy()

if df.empty:
    print("No data matched target dates.")
    exit(0)

# Merge Front Month logic
daily_vol = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df = df.reset_index().merge(front_months, on=['date', 'symbol'], how='inner').set_index('ts_event').sort_index()

df['time'] = df.index.time
df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3.0
df['pVol'] = df['hlc3'] * df['volume']
df['vwap'] = df.groupby('date')['pVol'].cumsum() / df.groupby('date')['volume'].cumsum()
df['vwap'] = df['vwap'].ffill()

fig = go.Figure()
buttons = []
TRACES_PER_DAY = 6

for i, trade_date in enumerate(target_dates):
    d_str = str(trade_date)
    day_df = df.loc[d_str]
    # Standard day session 09:30 to 16:00
    day_df = day_df[(day_df['time'] >= time(9, 30)) & (day_df['time'] <= time(16, 0))]
    
    if day_df.empty:
        continue
        
    trades_for_day = target_res[target_res['Date'] == d_str]
    if trades_for_day.empty:
        continue
    trade = trades_for_day.iloc[0]
    
    # Calculate ORB limits
    orb_m = (day_df['time'] >= time(9,30)) & (day_df['time'] < time(10,0))
    if day_df[orb_m].empty: continue
    orbH = day_df[orb_m]['high'].max()
    orbL = day_df[orb_m]['low'].min()
    
    visible = (i == len(target_dates) - 1)
    
    # 1. Candlesticks
    fig.add_trace(go.Candlestick(
        x=day_df.index, open=day_df['open'], high=day_df['high'], low=day_df['low'], close=day_df['close'],
        name=f"NQ {d_str}", visible=visible
    ))
    
    # 2. VWAP
    fig.add_trace(go.Scatter(
        x=day_df.index, y=day_df['vwap'], mode='lines', line=dict(color='#ff9800', width=2),
        name="VWAP", visible=visible
    ))
    
    # 3. & 4. ORB H/L
    fig.add_trace(go.Scatter(
        x=[day_df.index.min(), day_df.index.max()], y=[orbH, orbH], mode='lines', line=dict(color='#00e676', dash='dash'),
        name="ORB High", visible=visible
    ))
    fig.add_trace(go.Scatter(
        x=[day_df.index.min(), day_df.index.max()], y=[orbL, orbL], mode='lines', line=dict(color='#f44336', dash='dash'),
        name="ORB Low", visible=visible
    ))
    
    # 5. Entry
    e_time = pd.to_datetime(trade['Entry_Time']).tz_convert('US/Eastern') if trade['Entry_Time'] else None
    e_price = float(trade['Entry_Price'])
    dir_long = trade['Direction'] == 'Long'
    col_str = '#00ffff' if dir_long else '#ff00ff'
    
    fig.add_trace(go.Scatter(
        x=[e_time], y=[e_price], mode='markers',
        marker=dict(size=14, color=col_str, symbol='triangle-up' if dir_long else 'triangle-down', line=dict(width=2, color='white')),
        name=f"Entry ({trade['Direction']})", visible=visible,
        hovertemplate=f"Entry: {e_price:.2f}<br>{trade['Direction']}"
    ))
    
    # 6. Exit
    exit_pnl = float(trade['PnL'])
    exit_price = e_price + exit_pnl if dir_long else e_price - exit_pnl
    
    # reconstruct exact exit_time based on exit_reason
    exit_ts = None
    exit_path = day_df[day_df.index > e_time].copy() if e_time is not None else pd.DataFrame()
    if not exit_path.empty:
        if trade['Exit_Reason'] == "TimeClose":
            try:
                exit_ts = exit_path[exit_path['time'] >= time(15,55)].index[0]
            except:
                exit_ts = exit_path.index[-1]
        elif trade['Exit_Reason'] == "TP":
            try:
                exit_ts = exit_path[exit_path['high'] >= exit_price].index[0] if dir_long else exit_path[exit_path['low'] <= exit_price].index[0]
            except:
                exit_ts = exit_path.index[-1]
        elif trade['Exit_Reason'] == "SL":
            try:
                exit_ts = exit_path[exit_path['low'] <= exit_price].index[0] if dir_long else exit_path[exit_path['high'] >= exit_price].index[0]
            except:
                exit_ts = exit_path.index[-1]
    
    if exit_ts is None and not exit_path.empty:
        exit_ts = exit_path.index[-1]
        
    fig.add_trace(go.Scatter(
        x=[e_time, exit_ts], y=[e_price, exit_price],
        mode='lines+markers', line=dict(color=('#00ff00' if exit_pnl > 0 else '#ff0000'), width=3),
        marker=dict(size=10, symbol='x'),
        name=f"Exit ({trade['Exit_Reason']})", visible=visible,
        hovertemplate=f"Exit: {exit_price:.2f}<br>PnL: {exit_pnl:.2f}"
    ))

    # Add button
    is_win = float(trade['PnL']) > 0
    btn_label = f"{d_str} ({'[W]' if is_win else '[L]'} {trade['Direction']} {trade['PnL']:.1f}pts)"
    visibility = [False] * (len(target_dates) * TRACES_PER_DAY)
    for j in range(TRACES_PER_DAY):
        visibility[i * TRACES_PER_DAY + j] = True
        
    buttons.append(dict(label=btn_label, method="update", args=[{"visible": visibility}, {"title": f"ORB VWAP Retest - {btn_label}"}]))

print("Configuring Layout...")
fig.update_layout(
    title=f"ORB VWAP Real Execution (Last {len(target_dates)} trades)",
    updatemenus=[dict(active=len(target_dates)-1, buttons=buttons, x=0, y=1.05, xanchor="left", yanchor="bottom")],
    xaxis_rangeslider_visible=True,
    template="plotly_dark",
    height=800
)

# Export
fig.write_html(OUT_HTML, include_plotlyjs='cdn')
print("Successfully generated visualizer:", OUT_HTML)
