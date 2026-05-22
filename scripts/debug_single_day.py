import databento as db
import pandas as pd
import numpy as np
import os
from datetime import time, timedelta
import random

FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

print("Loading data for verification...")
store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

df_1m['hlc3'] = (df_1m['high'] + df_1m['low'] + df_1m['close']) / 3.0
df_1m['date'] = df_1m.index.date
df_1m['time'] = df_1m.index.time

# Calculate VWAP exactly as in backtest
df_1m['pVol'] = df_1m['hlc3'] * df_1m['volume']
df_1m['vwap'] = df_1m.groupby('date')['pVol'].cumsum() / df_1m.groupby('date')['volume'].cumsum()
df_1m['vwap'] = df_1m['vwap'].ffill()

dates = df_1m['date'].unique()

print("Searching for a sample trade to trace...")

for trade_date in reversed(dates):
    day_str = trade_date.strftime('%Y-%m-%d')
    day_data = df_1m.loc[day_str]
    if day_data.empty: continue
    
    orb_end_time = time(10, 0)
    SESSION_ENTRY_CUTOFF = time(12, 0)
    
    orb_mask = (day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)
    orb_bars = day_data[orb_mask]
    if orb_bars.empty: continue
    
    orbH = orb_bars['high'].max()
    orbL = orb_bars['low'].min()
    orbRange = orbH - orbL
    
    entry_window = day_data[(day_data['time'] >= orb_end_time) & (day_data['time'] <= SESSION_ENTRY_CUTOFF)]
    if entry_window.empty: continue
    
    has_traded = False
    pending_long = False
    pending_short = False
    entry_price = 0.0
    entry_time = None
    entry_dir = None
    sl_price = 0.0
    
    for idx, row in entry_window.iterrows():
        if has_traded: break
        was_pending_long = pending_long
        was_pending_short = pending_short
        
        if not pending_long and not pending_short:
            if row['high'] > orbH:
                pending_long = True
            if row['low'] < orbL:
                pending_short = True
                
        vwap_val = row['vwap']
        if was_pending_long:
            sl_price = orbL
            if vwap_val > sl_price and row['low'] <= vwap_val:
                entry_price = vwap_val if vwap_val <= row['high'] else row['high']
                entry_time = idx
                entry_dir = 'Long'
                has_traded = True
        elif was_pending_short:
            sl_price = orbH
            if vwap_val < sl_price and row['high'] >= vwap_val:
                entry_price = vwap_val if vwap_val >= row['low'] else row['low']
                entry_time = idx
                entry_dir = 'Short'
                has_traded = True
                
    if has_traded:
        print("="*60)
        print(f"TRACE FOR DATE: {day_str} | ORB_H: {orbH} | ORB_L: {orbL} | RANGE: {orbRange}")
        print(f"ENTRY: {entry_dir} triggered at {entry_time.time()} @ Price {entry_price:.2f}")
        print(f"SL_PRICE: {sl_price:.2f}")
        
        tp_size = 1.0
        tp_price = orbH + orbRange if entry_dir == 'Long' else orbL - orbRange
        print(f"TP_PRICE: {tp_price:.2f}")
        
        print("\n--- EXIT PATH EVALUATION ---")
        try:
            exit_idx_pos = day_data.index.get_loc(entry_time) + 1
            exit_path = day_data.iloc[exit_idx_pos:] if exit_idx_pos < len(day_data) else pd.DataFrame()
        except Exception as e:
            exit_path = pd.DataFrame()
            
        exit_time_val = None
        for e_idx, e_row in exit_path.iterrows():
            if e_row['time'] >= time(15, 55):
                print(f"[{e_idx.time()}] HIT TIME LIMIT. Close at {e_row['close']:.2f}")
                exit_time_val = e_idx
                break
                
            if entry_dir == 'Long':
                if e_row['low'] <= sl_price:
                    print(f"[{e_idx.time()}] HIT SL! Low ({e_row['low']}) <= SL ({sl_price})")
                    exit_time_val = e_idx
                    break
                elif e_row['high'] >= tp_price:
                    print(f"[{e_idx.time()}] HIT TP! High ({e_row['high']}) >= TP ({tp_price})")
                    exit_time_val = e_idx
                    break
            else:
                if e_row['high'] >= sl_price:
                    print(f"[{e_idx.time()}] HIT SL! High ({e_row['high']}) >= SL ({sl_price})")
                    exit_time_val = e_idx
                    break
                elif e_row['low'] <= tp_price:
                    print(f"[{e_idx.time()}] HIT TP! Low ({e_row['low']}) <= TP ({tp_price})")
                    exit_time_val = e_idx
                    break
        break
