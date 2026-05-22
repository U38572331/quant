import databento as db
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta, time

# --- Configuration ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_FILE = "nq_strategy_chart.html"

# Best Params from Analysis
ORB_MIN = 15
ENTRY_TYPE = '5m_Close' 
SL_MULT = 5
TP_MULT = 4
SESSION_START = time(9, 30)
SESSION_END_OFFSET = timedelta(hours=8)

print("Loading partial data (last 2 months to ensure 1 month coverage)...")
# Load only header + tail if possible? DBNStore reads all.
# We load and slice.
store = db.DBNStore.from_file(FILE_PATH)
df_all = store.to_df()
df_all.index = pd.to_datetime(df_all.index).tz_convert('US/Eastern')
df_all.sort_index(inplace=True)

# Slice last 1 month
end_date = df_all.index.max()
start_date = end_date - timedelta(days=30)
df = df_all[df_all.index >= start_date].copy()

print(f"Plotting data from {start_date} to {end_date}")

# Calculate ATR
def calculate_atr(high, low, close, period=10):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

df['ATR'] = calculate_atr(df['high'], df['low'], df['close'], 10)

# Resample 5m for signals
df_5m = df.resample('5min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last'
}).dropna()

# --- Simulation Logic ---
trades = []

dates = df.index.date
unique_dates = sorted(list(set(dates)))

for trade_date in unique_dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    day_data = df.loc[day_str]
    
    if day_data.empty: continue
    
    # Session
    session_start_dt = pd.Timestamp(f"{day_str} 09:30:00").tz_localize("US/Eastern")
    orb_end_dt = session_start_dt + timedelta(minutes=ORB_MIN)
    session_end_dt = session_start_dt + SESSION_END_OFFSET
    
    if session_start_dt not in day_data.index: continue
    
    # ORB Levels
    orb_slice = day_data.loc[session_start_dt : orb_end_dt] # Inclusive roughly
    # Exact check
    mask_orb = (day_data.index >= session_start_dt) & (day_data.index < orb_end_dt)
    orb_data = day_data[mask_orb]
    
    if orb_data.empty: continue
    
    orb_high = orb_data['high'].max()
    orb_low = orb_data['low'].min()
    
    # Trading Window
    trading_data = day_data.loc[orb_end_dt : session_end_dt]
    if trading_data.empty: continue
    
    # 5m data for triggering
    try:
        day_5m = df_5m.loc[day_str]
        future_5m = day_5m[day_5m.index >= orb_end_dt]
    except:
        continue
        
    # Find Entries
    # Long
    long_mask = future_5m['close'] > orb_high
    long_entries = future_5m[long_mask].index.tolist()
    
    # Short
    short_mask = future_5m['close'] < orb_low
    short_entries = future_5m[short_mask].index.tolist()
    
    # We need earliest entry
    possible_entries = []
    for t in long_entries: possible_entries.append((t, 'Long'))
    for t in short_entries: possible_entries.append((t, 'Short'))
    
    possible_entries.sort(key=lambda x: x[0])
    
    # Execute
    trades_today = 0
    current_idx = 0
    
    while trades_today < 2 and current_idx < len(possible_entries):
        entry_time, direction = possible_entries[current_idx]
        
        # Get Price and ATR at entry_time (Close of existing bar)
        # Entry time from 5m is the start? No resample index is usually start or left.
        # "Close of 5m bar > Level". 
        # If timestamp is 09:45, it covers 09:45-09:50. Close is at 09:50.
        # Databento/Pandas default is usually left-label.
        # Let's assume entry is at the END of that bar, i.e., time + 5min.
        # Or simply, we enter "at market" immediately upon condition met.
        
        # Refined: The logic backtest used was `index` of 5m bar.
        # If index is 09:45, closing logic checks 'close' of that bar.
        # Execution is on the NEXT bar's open? Or same bar close.
        # Backtest used "close" price of the trigger bar as entry.
        # So Entry Time = Bar Timestamp (for simplicity in plotting).
        
        try:
            entry_atr = df.asof(entry_time)['ATR'] # Use 1m ATR closest
            entry_price = df.asof(entry_time)['close']
        except:
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
            
        # Exit Simulation (1m data)
        trade_path = trading_data[trading_data.index > entry_time]
        
        exit_time = None
        exit_price = None
        result = 'EOD'
        
        if trade_path.empty:
            exit_time = trading_data.index[-1]
            exit_price = trading_data.iloc[-1]['close']
        else:
             # Fast Exit Check
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
            'Result': result,
            'SL': sl_price,
            'TP': tp_price
        })
        
        trades_today += 1
        
        # Advance index to after exit
        # Filter possible_entries
        new_idx = current_idx + 1
        while new_idx < len(possible_entries) and possible_entries[new_idx][0] <= exit_time:
            new_idx += 1
        current_idx = new_idx

print(f"Computed {len(trades)} trades.")

# --- Visualization ---
print("Generating Chart...")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)

# 1. Candlestick
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['open'], high=df['high'], low=df['low'], close=df['close'],
    name='OHLC'
), row=1, col=1)

# 2. Volume
colors = ['green' if row['close'] >= row['open'] else 'red' for index, row in df.iterrows()]
fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, name='Volume'), row=2, col=1)

# 3. Add Trades
for t in trades:
    color = 'green' if t['Direction'] == 'Long' else 'red'
    entry_marker = 'triangle-up' if t['Direction'] == 'Long' else 'triangle-down'
    
    # Entry Marker
    fig.add_trace(go.Scatter(
        x=[t['Entry_Time']], y=[t['Entry_Price']],
        mode='markers', marker=dict(symbol=entry_marker, size=12, color='white', line=dict(color=color, width=2)),
        name=f"Entry {t['Direction']}", showlegend=False
    ), row=1, col=1)
    
    # Exit Marker
    fig.add_trace(go.Scatter(
        x=[t['Exit_Time']], y=[t['Exit_Price']],
        mode='markers', marker=dict(symbol='x', size=10, color=color),
        name=f"Exit {t['Result']}", showlegend=False
    ), row=1, col=1)
    
    # Line connecting
    line_color = 'lime' if t['Result'] == 'TP' else 'red'
    if t['Result'] == 'EOD': line_color = 'gray'
    
    fig.add_trace(go.Scatter(
        x=[t['Entry_Time'], t['Exit_Time']], y=[t['Entry_Price'], t['Exit_Price']],
        mode='lines', line=dict(color=line_color, width=2, dash='dash'),
        showlegend=False
    ), row=1, col=1)

# Layout
fig.update_layout(
    template='plotly_dark',
    title=f"NQ Strategy Execution - Last 30 Days (ORB {ORB_MIN}m, 5m Close, SL x{SL_MULT}, TP x{TP_MULT})",
    xaxis_rangeslider_visible=False,
    height=900
)

import os
out_path = os.path.join(os.getcwd(), OUTPUT_FILE)
fig.write_html(out_path)
print(f"Chart saved to {out_path}")
