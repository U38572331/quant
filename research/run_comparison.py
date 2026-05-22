import pandas as pd
import numpy as np
from datetime import time, timedelta

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

def run_backtest(use_factors=False):
    trades = []
    for date, day_5m in df_5m.groupby('date'):
        day_1m = df_1m[df_1m['date'] == date].sort_index()
        orb_window = day_5m[(day_5m.index.time > time(9, 30)) & (day_5m.index.time <= time(10, 0))]
        if orb_window.empty: continue
        orb_h, orb_l = orb_window['high'].max(), orb_window['low'].min()
        orb_o, orb_c = orb_window.iloc[0]['open'], orb_window.iloc[-1]['close']
        orb_v = orb_window['volume'].sum()
        p_val = (orb_c - orb_o) * orb_v # Opening P
        
        if (orb_h - orb_l) < 5: continue
        
        trading_5m = day_5m[day_5m.index.time > time(10, 0)]
        state = "IDLE"
        for t5, bar5 in trading_5m.iterrows():
            if state == "IDLE" and t5.time() < time(15, 50):
                # 5m Breakout Bar Factors
                clv = ((bar5['close'] - bar5['low']) - (bar5['high'] - bar5['close'])) / (bar5['high'] - bar5['low']) if (bar5['high'] - bar5['low']) > 0 else 0
                
                is_long = bar5['close'] > orb_h
                is_short = bar5['close'] < orb_l
                
                if use_factors:
                    if is_long and not (clv > 0.6 and p_val > 0): continue
                    if is_short and not (clv < -0.6 and p_val < 0): continue
                
                if is_long or is_short:
                    state, pos_type = "POSITION", ("Long" if is_long else "Short")
                    entry_p = bar5['close']
                    sl_p = orb_l if is_long else orb_h
                    tp_p = entry_p + (entry_p - sl_p) if is_long else entry_p - (sl_p - entry_p)
                    risk = abs(entry_p - sl_p)
                    
                    exit_data = day_1m[day_1m.index > t5]
                    for t1, bar1 in exit_data.iterrows():
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
                            pnl_r = max(-1.0, min(1.0, ((exit_p - entry_p) if pos_type == "Long" else (entry_p - exit_p)) / risk))
                            trades.append({'date': date, 'type': pos_type, 'pnl_r': pnl_r})
                            state = "FINISHED"; break
                    if state == "FINISHED": break
    return pd.DataFrame(trades)

print("Running Comparison Backtests...")
raw_trades = run_backtest(use_factors=False)
opt_trades = run_backtest(use_factors=True)

raw_trades.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_compare.csv', index=False)
opt_trades.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_opt_compare.csv', index=False)
print("Backtests complete.")
