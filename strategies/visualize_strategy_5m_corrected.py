import databento as db
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta, time

# --- Configuration ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_FILE = "nq_strategy_chart_5m_corrected.html"

# Best Params from NATIVE 5m Analysis
# Based on output: 15m ORB, 5m Close, SL 2, TP 1 (Example adaptation from 1:0.36 profit factor? No PnL max was SL2 TP1)
# Let's use the actual max found. 
# Long: SL 2, TP 1. Short: SL 2, TP 2.
# Simplified for visualization: SL 2, TP 1.
ORB_MIN = 15
ENTRY_TYPE = '5m_Close' 
SL_MULT = 2
TP_MULT = 1
SESSION_START = time(9, 30)
SESSION_END_OFFSET = timedelta(hours=8)

print("Loading data...")
store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

# Slice last 30 days
end_date = df_1m.index.max()
start_date = end_date - timedelta(days=30)
df_slice = df_1m[df_1m.index >= start_date].copy()

# Resample to 5M (Native)
print("Resampling to 5m...")
df = df_slice.resample('5min', label='left', closed='left').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

# ATR on 5m
def calculate_atr(high, low, close, period=10):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

df['ATR'] = calculate_atr(df['high'], df['low'], df['close'], 10)

# --- Simulation Logic ---
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

# --- Plotting ---
print(f"Computed {len(trades)} trades on 5m chart.")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)

# 5M Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['open'], high=df['high'], low=df['low'], close=df['close'],
    name='5m Candles'
), row=1, col=1)

# Trades
for t in trades:
    color = 'green' if t['Direction'] == 'Long' else 'red'
    marker = 'triangle-up' if t['Direction'] == 'Long' else 'triangle-down'
    
    fig.add_trace(go.Scatter(
        x=[t['Entry_Time']], y=[t['Entry_Price']],
        mode='markers', marker=dict(symbol=marker, size=14, color=color, line=dict(color='white', width=1)),
        showlegend=False
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=[t['Exit_Time']], y=[t['Exit_Price']],
        mode='markers', marker=dict(symbol='x', size=10, color='yellow'),
        showlegend=False
    ), row=1, col=1)
    
    line_col = 'lime' if t['Result'] == 'TP' else 'red'
    if t['Result'] == 'EOD': line_col = 'white'
    
    fig.add_trace(go.Scatter(
        x=[t['Entry_Time'], t['Exit_Time']], y=[t['Entry_Price'], t['Exit_Price']],
        mode='lines', line=dict(color=line_col, width=2),
        showlegend=False
    ), row=1, col=1)

# Remove Gaps - Hide Sat/Sun
fig.update_xaxes(
    rangebreaks=[
        dict(bounds=["sat", "mon"]), # Hide weekends
        dict(bounds=[17, 9.5], pattern="hour"), # Hide non-trading hours (17:00 to 09:30)
    ]
)

fig.update_layout(
    template='plotly_dark',
    title="NQ Strategy (Corrected Native 5m) - Last 30 Days",
    xaxis_rangeslider_visible=False,
    height=900
)

import os
out_path = os.path.join(os.getcwd(), OUTPUT_FILE)
fig.write_html(out_path)
print(f"Corrected 5m Chart saved to {out_path}")
