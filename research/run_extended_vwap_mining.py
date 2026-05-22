import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time, timedelta

# 1. LOAD DATA
print("Loading Master NQ data for Extended VWAP Mining...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')

# Clean Front-Month
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-', na=False)]
df = df[~df['symbol'].str.startswith('MNQ')]
df = df.sort_values(['ts_event', 'volume'], ascending=[True, False]).groupby(df.index).first()
df = df[df.index >= '2021-01-01'].copy() # Focus on 2021+ for faster iteration

# 2. EXTENDED VWAP ENGINE
# We need to calculate cumulative VWAP across dates. 
# ETH starts at 18:00 (prev day).
print("Calculating Extended VWAPs...")
df['pv'] = df['close'] * df['volume']

# Pre-calculate Yesterday's Final Values
daily_final = {}
for date, day in df.groupby(df.index.date):
    # RTH final (09:30-16:00)
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    y_rth_val = rth['pv'].sum() / rth['volume'].sum() if not rth.empty else np.nan
    # Full Session final (starts from 18:00 previous day, but here we take the whole day for simplicity)
    # Actually, a better way is to define session-based accumulation.
    y_eth_val = day['pv'].sum() / day['volume'].sum() if not day.empty else np.nan
    daily_final[date] = {'rth': y_rth_val, 'eth': y_eth_val}

# 3. COMBINATION MINING
trades = []
dates = sorted(np.unique(df.index.date))
for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df.index.date == curr_d].sort_index()
    
    # Yesterday's Levels (Extended)
    y_rth = daily_final.get(prev_d, {}).get('rth', np.nan)
    y_eth = daily_final.get(prev_d, {}).get('eth', np.nan)
    
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
            
            # Current Extended VWAPs (Cumulative up to T)
            # C_RTH: Cumulative from 09:30
            c_rth_df = day[(day.index.time >= time(9,30)) & (day.index <= t)]
            c_rth = c_rth_df['pv'].sum() / c_rth_df['volume'].sum()
            
            # C_ETH: Cumulative from day start (Approx 18:00 prev to current T)
            c_eth_df = day[day.index <= t] # Simplified since DBN is date-split mostly
            c_eth = c_eth_df['pv'].sum() / c_eth_df['volume'].sum()
            
            # 4 Features (1=Above, 0=Below)
            features = (1 if entry > c_rth else 0, 1 if entry > c_eth else 0,
                        1 if entry > y_rth else 0, 1 if entry > y_eth else 0)
            
            # Outcome
            sl = orb_l if is_long else orb_h
            tp = entry + (entry - sl) if is_long else entry - (sl - entry)
            risk = abs(entry - sl)
            if risk < 5: break
            
            pnl = -1.0
            exit_data = day[day.index > t]
            for te, be in exit_data.iterrows():
                if is_long:
                    if be['low'] <= sl: pnl = -1.0; break
                    elif be['high'] >= tp: pnl = 1.0; break
                    elif te.time() >= time(15,55): pnl = (be['close'] - entry)/risk; break
                else:
                    if be['high'] >= sl: pnl = -1.0; break
                    elif be['low'] <= tp: pnl = 1.0; break
                    elif te.time() >= time(15,55): pnl = (entry - be['close'])/risk; break
            
            trades.append({
                'type': 'Long' if is_long else 'Short', 'pnl': pnl,
                'c_rth': features[0], 'c_eth': features[1], 
                'y_rth': features[2], 'y_eth': features[3]
            })
            break

results_df = pd.DataFrame(trades)
results_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_extended_vwap_mining.csv', index=False)
print("Extended VWAP Mining Complete.")
