import databento as db
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta, time

# --- Configuration ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_FILE = "nq_strategy_chart_final.html"

# Best Params (Native 5m)
ORB_MIN = 15
ENTRY_TYPE = '5m_Close' 
SL_MULT = 2
TP_MULT = 1
SESSION_START = time(9, 30)
SESSION_END_OFFSET = timedelta(hours=8)

print("Loading data...")
store = db.DBNStore.from_file(FILE_PATH)
df_all = store.to_df()
df_all.index = pd.to_datetime(df_all.index).tz_convert('US/Eastern')
df_all.sort_index(inplace=True)

# Slice last 30 days
end_date = df_all.index.max()
start_date = end_date - timedelta(days=30)
df_1m = df_all[df_all.index >= start_date].copy()

# Resample to 5M (Native)
print("Resampling to 5m...")
df = df_1m.resample('5min', label='left', closed='left').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

# Calculate ATR on FULL 5m set (to be accurate)
def calculate_atr(high, low, close, period=10):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

df['ATR'] = calculate_atr(df['high'], df['low'], df['close'], 10)

# --- Simulation Logic (Run on Date Basis) ---
trades = []
dates = df.index.date
unique_dates = sorted(list(set(dates)))

for trade_date in unique_dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    day_data = df.loc[day_str]
    
    if day_data.empty: continue
    
    session_start_dt = pd.Timestamp(f"{day_str} 09:30:00").tz_localize("US/Eastern")
    orb_end_dt = session_start_dt + timedelta(minutes=ORB_MIN)
    session_end_dt = session_start_dt + SESSION_END_OFFSET
    
    if session_start_dt not in day_data.index: continue
    
    mask_orb = (day_data.index >= session_start_dt) & (day_data.index < orb_end_dt)
    orb_data = day_data[mask_orb]
    if orb_data.empty: continue
    
    orb_high = orb_data['high'].max()
    orb_low = orb_data['low'].min()
    
    trading_data = day_data.loc[orb_end_dt : session_end_dt]
    if trading_data.empty: continue
    
    # Entries
    future_data = trading_data
    
    long_mask = future_data['close'] > orb_high
    long_entries = future_data[long_mask].index.tolist()
    
    short_mask = future_data['close'] < orb_low
    short_entries = future_data[short_mask].index.tolist()
    
    possible_entries = []
    for t in long_entries: possible_entries.append((t, 'Long'))
    for t in short_entries: possible_entries.append((t, 'Short'))
    possible_entries.sort(key=lambda x: x[0])
    
    trades_today = 0
    current_idx = 0
    
    while trades_today < 2 and current_idx < len(possible_entries):
        entry_time, direction = possible_entries[current_idx]
        
        try:
            entry_atr = df.at[entry_time, 'ATR']
            entry_price = df.at[entry_time, 'close']
        except:
            current_idx += 1
            continue
            
        if pd.isna(entry_atr): 
            current_idx += 1
            continue

        sl_dist = entry_atr * SL_MULT
        tp_dist = entry_atr * TP_MULT
        
        if direction == 'Long':
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
        else:
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist
            
        trade_path = trading_data[trading_data.index > entry_time]
        
        exit_time = None
        exit_price = None
        result = 'EOD'
        
        if trade_path.empty:
            exit_time = trading_data.index[-1]
            exit_price = trading_data.iloc[-1]['close']
        else:
             if direction == 'Long':
                 hit_sl = trade_path['low'] <= sl_price
                 hit_tp = trade_path['high'] >= tp_price
                 f_sl = hit_sl.idxmax() if hit_sl.any() else None
                 f_tp = hit_tp.idxmax() if hit_tp.any() else None
                 
                 if f_sl and f_tp:
                     if f_sl < f_tp: 
                         exit_time = f_sl
                         exit_price = sl_price
                         result = 'SL'
                     else:
                         exit_time = f_tp
                         exit_price = tp_price
                         result = 'TP'
                 elif f_sl:
                     exit_time = f_sl
                     exit_price = sl_price
                     result = 'SL'
                 elif f_tp:
                     exit_time = f_tp
                     exit_price = tp_price
                     result = 'TP'
             else:
                 hit_sl = trade_path['high'] >= sl_price
                 hit_tp = trade_path['low'] <= tp_price
                 f_sl = hit_sl.idxmax() if hit_sl.any() else None
                 f_tp = hit_tp.idxmax() if hit_tp.any() else None
                 
                 if f_sl and f_tp:
                     if f_sl < f_tp:
                         exit_time = f_sl
                         exit_price = sl_price
                         result = 'SL'
                     else:
                         exit_time = f_tp
                         exit_price = tp_price
                         result = 'TP'
                 elif f_sl:
                     exit_time = f_sl
                     exit_price = sl_price
                     result = 'SL'
                 elif f_tp:
                     exit_time = f_tp
                     exit_price = tp_price
                     result = 'TP'
                     
             if not exit_time:
                 exit_time = trade_path.index[-1]
                 exit_price = trade_path.iloc[-1]['close']

        trades.append({
            'Entry_Time': entry_time,
            'Entry_Price': entry_price,
            'Direction': direction,
            'Exit_Time': exit_time,
            'Exit_Price': exit_price,
            'Result': result
        })
        trades_today += 1
        
        new_idx = current_idx + 1
        while new_idx < len(possible_entries) and possible_entries[new_idx][0] <= exit_time:
            new_idx += 1
        current_idx = new_idx

# --- VISUALIZATION PREP ---
# 1. Filter Data for RTH Only (09:30 - 16:00)
print("Filtering for Visualization (RTH 09:30-16:00, No Weekends)...")
df_plot = df.between_time('09:30', '16:00').copy()
df_plot = df_plot[df_plot.index.dayofweek < 5] # 0-4 is Mon-Fri

# 2. Create String Index
df_plot['DateStr'] = df_plot.index.strftime('%Y-%m-%d %H:%M')

print(f"Plotting {len(df_plot)} bars...")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)

# 3. Candles with Category Axis
fig.add_trace(go.Candlestick(
    x=df_plot['DateStr'],
    open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'],
    name='5m Candles'
), row=1, col=1)

colors = ['green' if row['close'] >= row['open'] else 'red' for index, row in df_plot.iterrows()]
fig.add_trace(go.Bar(
    x=df_plot['DateStr'], 
    y=df_plot['volume'], 
    marker_color=colors, 
    name='Volume'
), row=2, col=1)

# 4. Map Trades to String Labels
# Since we might have trades executing at e.g. 16:05 (if allowed), but we filter to 16:00.
# The previous logic had tradeSession to 8 hours (09:30+8 = 17:30).
# If we cut the chart at 16:00, we might miss the exit marker.
# Let's adjust filter to cover the 8h session if possible, or just clamp markers.
# For ORB lines etc, simpler to see 09:30-16:15 usually suitable for NQ RTH.
# Let's try 16:15 to catch EOD closes.

valid_dates = set(df_plot['DateStr'])

for t in trades:
    # Convert timestamps to string format
    ent_s = t['Entry_Time'].strftime('%Y-%m-%d %H:%M')
    ext_s = t['Exit_Time'].strftime('%Y-%m-%d %H:%M')
    
    # Check visuals availability
    if ent_s not in valid_dates:
        # Try finding closest? No, if it's outside RTH we skip or clamp
        # ORB strategy should be in RTH.
        continue
        
    # If Exit is outside (e.g. 16:20), we can't plot the line to it easily on category axis
    # unless we add that category. 
    # But usually exits are EOD ~16:00.
    if ext_s not in valid_dates:
        # Just plot entry marker? Or skip line?
        pass
    
    color = 'green' if t['Direction'] == 'Long' else 'red'
    marker = 'triangle-up' if t['Direction'] == 'Long' else 'triangle-down'
    
    fig.add_trace(go.Scatter(
        x=[ent_s], y=[t['Entry_Price']],
        mode='markers', marker=dict(symbol=marker, size=15, color=color, line=dict(color='white', width=1)),
        showlegend=False
    ), row=1, col=1)
    
    if ext_s in valid_dates:
        fig.add_trace(go.Scatter(
            x=[ext_s], y=[t['Exit_Price']],
            mode='markers', marker=dict(symbol='x', size=10, color='yellow'),
            showlegend=False
        ), row=1, col=1)
        
        line_col = 'lime' if t['Result'] == 'TP' else 'red'
        if t['Result'] == 'EOD': line_col = 'white'
        
        fig.add_trace(go.Scatter(
            x=[ent_s, ext_s], y=[t['Entry_Price'], t['Exit_Price']],
            mode='lines', line=dict(color=line_col, width=2),
            showlegend=False
        ), row=1, col=1)

# Axis Configuration
fig.update_xaxes(type='category', showgrid=False, tickmode='auto', nticks=20)
fig.update_layout(
    template='plotly_dark',
    title="NQ Strategy (RTH Only 09:30-16:00) - No Gaps",
    xaxis_rangeslider_visible=False,
    height=900,
    bargap=0.1
)

import os
out_path = os.path.join(os.getcwd(), OUTPUT_FILE)
fig.write_html(out_path)
print(f"Final Chart saved to {out_path}")
