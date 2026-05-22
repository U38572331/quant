import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
df_1m = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')
df_1m = df_1m[df_1m.index >= '2020-01-01'].copy()
df_1m['date'] = df_1m.index.date

# Resample to 5m
def resample_day(group):
    return group.resample('5min', label='right', closed='right').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()

df_5m = df_1m.groupby('date').apply(resample_day).reset_index(level=0, drop=True)
df_5m['date'] = df_5m.index.date

trades = []

print("Running Corrected 5m Backtest (Filtering Narrow Ranges)...")
for date, day_5m in df_5m.groupby('date'):
    day_1m = df_1m[df_1m['date'] == date].sort_index()
    
    orb_window = day_5m[(day_5m.index.time > time(9, 30)) & (day_5m.index.time <= time(10, 0))]
    if orb_window.empty: continue
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # FILTER: If ORB range is too narrow (< 5 points), skip
    if (orb_h - orb_l) < 5: continue
    
    trading_5m = day_5m[day_5m.index.time > time(10, 0)]
    state = "IDLE"
    
    for t5, bar5 in trading_5m.iterrows():
        if state == "IDLE":
            if t5.time() < time(15, 50):
                if bar5['close'] > orb_h:
                    state, pos_type = "POSITION", "Long"
                    entry_p = bar5['close']
                    sl_p = orb_l
                    tp_p = entry_p + (entry_p - sl_p)
                    entry_t = t5
                elif bar5['close'] < orb_l:
                    state, pos_type = "POSITION", "Short"
                    entry_p = bar5['close']
                    sl_p = orb_h
                    tp_p = entry_p - (sl_p - entry_p)
                    entry_t = t5
                
                if state == "POSITION":
                    risk_pts = abs(entry_p - sl_p)
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
                            pnl_pts = (exit_p - entry_p) if pos_type == "Long" else (entry_p - exit_p)
                            pnl_r = pnl_pts / risk_pts
                            # CAP PnL_R to avoid outliers
                            pnl_r = max(-1.1, min(1.1, pnl_r))
                            trades.append({'date': date, 'type': pos_type, 'pnl_r': pnl_r, 'pnl_pts': pnl_pts})
                            state = "FINISHED"
                            break
                    if state == "FINISHED": break

trades_df = pd.DataFrame(trades)
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_trades_5m_fixed.csv', index=False)
print(f"Fixed Backtest Done. Trades: {len(trades_df)}")
