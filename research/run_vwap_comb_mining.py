import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time, timedelta

# 1. LOAD AND PREPARE DATA
print("Loading Master NQ data for combination mining...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')

# Continuous Front-Month Logic
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-', na=False)]
df = df[~df['symbol'].str.startswith('MNQ')]
df = df.sort_values(['ts_event', 'volume'], ascending=[True, False]).groupby(df.index).first()
df = df[df.index >= '2020-01-01'].copy()
df['date'] = df.index.date

# 2. VWAP CALCULATION (RTH & ETH)
levels = {}
for date, day in df.groupby('date'):
    rth_df = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth_df['close'] * rth_df['volume']).sum() / rth_df['volume'].sum() if not rth_df.empty else np.nan
    eth_df = day[day.index.time < time(9,30)]
    eth_v = (eth_df['close'] * eth_df['volume']).sum() / eth_df['volume'].sum() if not eth_df.empty else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v, 'rth_df': rth_df, 'eth_df': eth_df}

# 3. COMBINATION SWEEP BACKTEST
trades = []
dates = sorted(df['date'].unique())
for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df['date'] == curr_d].sort_index()
    
    # The 4 VWAP Levels
    prev_rth = levels.get(prev_d, {}).get('rth', np.nan)
    prev_eth = levels.get(prev_d, {}).get('eth', np.nan)
    curr_eth = levels.get(curr_d, {}).get('eth', np.nan)
    # Current RTH VWAP (will be calculated dynamically at breakout)
    
    if any(np.isnan(x) for x in [prev_rth, prev_eth, curr_eth]): continue
    
    orb = day[(day.index.time >= time(9,30)) & (day.index.time <= time(10,0))]
    if orb.empty: continue
    orb_h, orb_l = orb['high'].max(), orb['low'].min()
    
    trading = day[day.index.time > time(10,0)]
    for t, bar in trading.iterrows():
        if t.time() > time(15, 50): break
        is_long = bar['close'] > orb_h
        is_short = bar['close'] < orb_l
        if is_long or is_short:
            entry = bar['close']
            
            # Dynamic Current RTH VWAP (from 09:30 to entry time)
            c_rth_df = day[(day.index.time >= time(9,30)) & (day.index <= t)]
            curr_rth = (c_rth_df['close'] * c_rth_df['volume']).sum() / c_rth_df['volume'].sum()
            
            # Feature Extraction (1 if above, 0 if below)
            f_y_rth = 1 if entry > prev_rth else 0
            f_y_eth = 1 if entry > prev_eth else 0
            f_c_rth = 1 if entry > curr_rth else 0
            f_c_eth = 1 if entry > curr_eth else 0
            
            # Simplified PnL
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
                'y_rth': f_y_rth, 'y_eth': f_y_eth, 'c_rth': f_c_rth, 'c_eth': f_c_eth
            })
            break

results_df = pd.DataFrame(trades)
results_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_vwap_comb_mining.csv', index=False)
print("VWAP Combination Mining Data Generated.")
