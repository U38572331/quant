import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')
df = df[df.index >= '2025-12-01'].copy()
df['date'] = df.index.date

detailed_trades = []

for date, day_data in df.groupby('date'):
    day_data = day_data.sort_index()
    orb_window = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time < time(10, 0))]
    if orb_window.empty: continue
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    trading_data = day_data[day_data.index.time >= time(10, 0)]
    bars = trading_data.to_dict('records')
    times = trading_data.index
    
    state = "IDLE"
    pos_type, entry_p, sl_p, tp_p, entry_t = None, 0, 0, 0, None
    
    for i in range(len(bars)):
        bar, curr_t = bars[i], times[i]
        if state == "IDLE":
            if curr_t.time() < time(15, 50):
                if bar['close'] > orb_h: state, pos_type = "PENDING", "Long"
                elif bar['close'] < orb_l: state, pos_type = "PENDING", "Short"
        elif state == "PENDING":
            entry_p, entry_t = bar['open'], curr_t
            if pos_type == "Long":
                sl_p, tp_p = orb_l, bar['open'] + (bar['open'] - orb_l)
            else:
                sl_p, tp_p = orb_h, bar['open'] - (orb_h - bar['open'])
            state = "POSITION"
        elif state == "POSITION":
            exit_p, reason = None, ""
            if pos_type == "Long":
                if bar['low'] <= sl_p: exit_p, reason = sl_p, "SL"
                elif bar['high'] >= tp_p: exit_p, reason = tp_p, "TP"
                elif curr_t.time() >= time(15, 55): exit_p, reason = bar['close'], "EOD"
            else:
                if bar['high'] >= sl_p: exit_p, reason = sl_p, "SL"
                elif bar['low'] <= tp_p: exit_p, reason = tp_p, "TP"
                elif curr_t.time() >= time(15, 55): exit_p, reason = bar['close'], "EOD"
            
            if exit_p:
                pnl_pts = (exit_p - entry_p) if pos_type == "Long" else (entry_p - exit_p)
                pnl_r = pnl_pts / abs(entry_p - sl_p)
                detailed_trades.append({
                    'Date': date, 'Type': pos_type, 'ORB_H': orb_h, 'ORB_L': orb_l,
                    'Entry': entry_p, 'SL': sl_p, 'TP': tp_p, 'Exit': exit_p,
                    'Reason': reason, 'PnL_R': pnl_r
                })
                break

audit_df = pd.DataFrame(detailed_trades)
print(audit_df.to_string())
audit_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_audit_2025.csv', index=False)
