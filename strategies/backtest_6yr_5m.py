import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
print("Loading data for 5m-Confirmation Backtest...")
df_1m = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')
df_1m = df_1m[df_1m.index >= '2020-01-01'].copy()
df_1m['date'] = df_1m.index.date

# Resample to 5m
print("Resampling to 5m bars...")
def resample_day(group):
    # Standard OHLCV resampling
    return group.resample('5min', label='right', closed='right').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'symbol': 'first'
    }).dropna()

df_5m = df_1m.groupby('date').apply(resample_day).reset_index(level=0, drop=True)
df_5m['date'] = df_5m.index.date

trades = []

print("Running Backtest (5m Breakout Confirmation)...")
for date, day_5m in df_5m.groupby('date'):
    day_1m = df_1m[df_1m['date'] == date].sort_index()
    
    # ORB (09:30 - 10:00) using 5m bars
    orb_window = day_5m[(day_5m.index.time > time(9, 30)) & (day_5m.index.time <= time(10, 0))]
    if orb_window.empty: continue
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # Trading (From 10:00)
    trading_5m = day_5m[day_5m.index.time > time(10, 0)]
    
    state = "IDLE"
    pos_type, entry_p, sl_p, tp_p = None, 0, 0, 0
    
    for t5, bar5 in trading_5m.iterrows():
        if state == "IDLE":
            if t5.time() < time(15, 50):
                # 5m Bar Close Confirmation
                if bar5['close'] > orb_h:
                    state, pos_type = "POSITION", "Long"
                    entry_p = bar5['close'] # Enter at 5m close
                    sl_p, tp_p = orb_l, entry_p + (entry_p - orb_l)
                    entry_t = t5
                elif bar5['close'] < orb_l:
                    state, pos_type = "POSITION", "Short"
                    entry_p = bar5['close'] # Enter at 5m close
                    sl_p, tp_p = orb_h, entry_p - (orb_h - entry_p)
                    entry_t = t5
                
                if state == "POSITION":
                    # After entry, check SL/TP using 1m data from entry_t onwards
                    exit_data_1m = day_1m[day_1m.index >= entry_t]
                    for t1, bar1 in exit_data_1m.iterrows():
                        exit_p = None
                        if pos_type == "Long":
                            if bar1['low'] <= sl_p: exit_p = sl_p
                            elif bar1['high'] >= tp_p: exit_p = tp_p
                            elif t1.time() >= time(15, 55): exit_p = bar1['close']
                        else:
                            if bar1['high'] >= sl_p: exit_p = sl_p
                            elif bar1['low'] <= tp_p: exit_p = tp_p
                            elif t1.time() >= time(15, 55): exit_p = bar1['close']
                        
                        if exit_p:
                            pnl_r = ((exit_p - entry_p) if pos_type == "Long" else (entry_p - exit_p)) / abs(entry_p - sl_p)
                            trades.append({'date': date, 'type': pos_type, 'pnl_r': pnl_r})
                            state = "FINISHED"
                            break
                    if state == "FINISHED": break

trades_df = pd.DataFrame(trades)
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_trades_5m.csv', index=False)
print(f"5m-Confirmation Backtest Done. Total Trades: {len(trades_df)}")
if not trades_df.empty:
    print(f"Win Rate: {(trades_df['pnl_r'] > 0).mean()*100:.2f}%")
