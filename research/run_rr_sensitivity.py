import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import time, timedelta

# 1. LOAD MASTER DATA
print("Running Multi-RR Sensitivity Analysis...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')

# Clean Front-Month
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-', na=False)]
df = df[~df['symbol'].str.startswith('MNQ')]
df = df.sort_values(['ts_event', 'volume'], ascending=[True, False]).groupby(df.index).first()
df = df[df.index >= '2021-01-01'].copy()
df['date'] = df.index.date
df['pv'] = df['close'] * df['volume']

# VWAP Levels Cache
levels = {}
for date, day in df.groupby('date'):
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth['pv'].sum() / rth['volume'].sum()) if not rth.empty else np.nan
    eth_v = (day['pv'].sum() / day['volume'].sum()) if not day.empty else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v}

# 2. RR SENSITIVITY BACKTEST
rr_list = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 2.0, 2.5]
results = []
dates = sorted(df['date'].unique())

for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df['date'] == curr_d].sort_index()
    y_rth, y_eth = levels.get(prev_d, {}).get('rth', np.nan), levels.get(prev_d, {}).get('eth', np.nan)
    if np.isnan(y_rth) or np.isnan(y_eth): continue
    
    orb_h = day[(day.index.time >= time(9,30)) & (day.index.time <= time(10,0))]['high'].max()
    orb_l = day[(day.index.time >= time(9,30)) & (day.index.time <= time(10,0))]['low'].min()
    
    trading = day[day.index.time > time(10,0)]
    for t, bar in trading.iterrows():
        if t.time() > time(15, 50): break
        is_long = bar['close'] > orb_h
        is_short = bar['close'] < orb_l
        if is_long or is_short:
            entry = bar['close']
            # Dynamic VWAPs
            c_rth_df = day[(day.index.time >= time(9,30)) & (day.index <= t)]
            c_rth = c_rth_df['pv'].sum() / c_rth_df['volume'].sum()
            c_eth_df = day[day.index <= t]
            c_eth = c_eth_df['pv'].sum() / c_eth_df['volume'].sum()
            
            # V3 FILTERS
            if is_long:
                if not (entry > c_rth and entry > c_eth and entry > y_rth and entry > y_eth): break
            else:
                if not (entry < c_rth and entry < c_eth and entry > y_rth and entry > y_eth): break
            
            sl = orb_l if is_long else orb_h
            risk = abs(entry - sl)
            if risk < 5: break
            
            # TEST MULTIPLE RRs
            exit_data = day[day.index > t]
            for rr in rr_list:
                tp = entry + rr * (entry - sl) if is_long else entry - rr * (sl - entry)
                pnl = -1.0
                for te, be in exit_data.iterrows():
                    if is_long:
                        if be['low'] <= sl: pnl = -1.0; break
                        elif be['high'] >= tp: pnl = rr; break
                        elif te.time() >= time(15,55): pnl = (be['close'] - entry)/risk; break
                    else:
                        if be['high'] >= sl: pnl = -1.0; break
                        elif be['low'] <= tp: pnl = rr; break
                        elif te.time() >= time(15,55): pnl = (entry - be['close'])/risk; break
                
                results.append({'type': 'Long' if is_long else 'Short', 'rr_target': rr, 'pnl': pnl})
            break

results_df = pd.DataFrame(results)
results_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_rr_sensitivity_data.csv', index=False)
print("RR Sensitivity Data Generated.")
