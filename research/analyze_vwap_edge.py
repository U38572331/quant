import databento as db
import pandas as pd
import numpy as np
from datetime import time, timedelta

# 1. Load RAW Data (Need ETH/Overnight)
print("Loading FULL DBN data to calculate ETH VWAPs...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
# We only need the last few years for efficiency in this multi-VWAP audit
# But let's try to process a significant chunk
data = db.DBNStore.from_file(path)
df = data.to_df()

# Cleanup and TZ
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
df['date'] = df.index.date
df['time'] = df.index.time

# 2. VWAP Calculation Engine
def calc_vwaps(df):
    # RTH (09:30 - 16:00)
    # ETH (18:00 prev - 09:30 current)
    
    # Calculate VWAP for each session
    # Simplified: We need daily snapshots
    results = {}
    
    for date, day_data in df.groupby('date'):
        # RTH VWAP
        rth = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time <= time(16, 0))]
        if not rth.empty:
            rth_vwap = (rth['close'] * rth['volume']).sum() / rth['volume'].sum()
        else: rth_vwap = np.nan
        
        # ETH VWAP (Approximate as the morning period 00:00 - 09:30 for simplicity in this pass)
        eth = day_data[(day_data.index.time < time(9, 30))]
        if not eth.empty:
            eth_vwap = (eth['close'] * eth['volume']).sum() / eth['volume'].sum()
        else: eth_vwap = np.nan
        
        results[date] = {'rth_vwap': rth_vwap, 'eth_vwap': eth_vwap}
    return results

vwap_map = calc_vwaps(df)

# 3. Enhanced Backtest with VWAP Factors
trades = []
dates = sorted(df['date'].unique())

for i in range(1, len(dates)):
    curr_date = dates[i]
    prev_date = dates[i-1]
    
    day_data = df[df['date'] == curr_date].sort_index()
    
    # VWAP Factors
    y_rth = vwap_map.get(prev_date, {}).get('rth_vwap', np.nan)
    y_eth = vwap_map.get(prev_date, {}).get('eth_vwap', np.nan)
    
    # Current morning ETH VWAP
    c_eth = vwap_map.get(curr_date, {}).get('eth_vwap', np.nan)
    
    # ORB
    orb_window = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time <= time(10, 0))]
    if orb_window.empty: continue
    orb_h, orb_l = orb_window['high'].max(), orb_window['low'].min()
    
    # Entry detection
    trading = day_data[day_data.index.time > time(10, 0)]
    for t, bar in trading.iterrows():
        if t.time() > time(15, 50): break
        
        is_long = bar['close'] > orb_h
        is_short = bar['close'] < orb_l
        
        if is_long or is_short:
            # Entry Price
            entry = bar['close']
            
            # VWAP Relative Positions (Edge Hunting)
            # 1. Distance to Prev RTH VWAP
            d_y_rth = (entry - y_rth) / entry if not np.isnan(y_rth) else 0
            # 2. Distance to Morning ETH VWAP
            d_c_eth = (entry - c_eth) / entry if not np.isnan(c_eth) else 0
            
            # Simple Backtest Result
            sl = orb_l if is_long else orb_h
            tp = entry + (entry - sl) if is_long else entry - (sl - entry)
            risk = abs(entry - sl)
            if risk < 5: break
            
            # Check outcome
            outcome = 0
            exit_data = day_data[day_data.index > t]
            for t_ex, bar_ex in exit_data.iterrows():
                if is_long:
                    if bar_ex['low'] <= sl: outcome = -1.0; break
                    elif bar_ex['high'] >= tp: outcome = 1.0; break
                    elif t_ex.time() >= time(15, 55): outcome = (bar_ex['close'] - entry)/risk; break
                else:
                    if bar_ex['high'] >= sl: outcome = -1.0; break
                    elif bar_ex['low'] <= tp: outcome = 1.0; break
                    elif t_ex.time() >= time(15, 55): outcome = (entry - bar_ex['close'])/risk; break
            
            trades.append({
                'date': curr_date, 'type': 'Long' if is_long else 'Short', 'pnl': outcome,
                'y_rth_dist': d_y_rth, 'c_eth_dist': d_c_eth, 'y_eth_dist': (entry - y_eth)/entry if not np.isnan(y_eth) else 0
            })
            break

trades_df = pd.DataFrame(trades)
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_vwap_edge_analysis.csv', index=False)
print("VWAP Edge data generated.")
