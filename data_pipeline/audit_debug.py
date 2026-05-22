import databento as db
import pandas as pd
import numpy as np
from datetime import time, timedelta

# 1. LOAD SUBSET
print("Auditing last 10 days of trades...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
df = df[df.index >= '2025-11-01'].copy() # Focus on the very end
df['date'] = df.index.date

# 2. VWAP LEVELS
levels = {}
for date, day in df.groupby('date'):
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth['close'] * rth['volume']).sum() / rth['volume'].sum() if not rth.empty else np.nan
    eth = day[day.index.time < time(9,30)]
    eth_v = (eth['close'] * eth['volume']).sum() / eth['volume'].sum() if not eth.empty else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v}

# 3. AUDIT LOOP
dates = sorted(df['date'].unique())
for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df['date'] == curr_d].sort_index()
    y_rth = levels.get(prev_d, {}).get('rth', np.nan)
    c_eth = levels.get(curr_d, {}).get('eth', np.nan)
    
    orb = day[(day.index.time >= time(9,30)) & (day.index.time <= time(10,0))]
    if orb.empty: continue
    orb_h, orb_l = orb['high'].max(), orb['low'].min()
    
    print(f"\n--- DATE: {curr_d} ---")
    print(f"ORB: {orb_l:.2f} - {orb_h:.2f} | PrevRTH: {y_rth:.2f} | MorningETH: {c_eth:.2f}")
    
    trading = day[day.index.time > time(10,0)]
    for t, bar in trading.iterrows():
        is_long = bar['close'] > orb_h
        is_short = bar['close'] < orb_l
        
        if is_long or is_short:
            entry = bar['close']
            sl = orb_l if is_long else orb_h
            tp = entry + (entry - sl) if is_long else entry - (sl - entry)
            print(f"SIGNAL @ {t.time()}: {'LONG' if is_long else 'SHORT'} | Entry: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")
            
            # Check Confluence
            conf = (entry > y_rth and entry > c_eth) if is_long else (entry < y_rth and entry < c_eth)
            print(f"Confluence: {conf}")
            
            exit_data = day[day.index > t].head(30) # Look at next 30 mins
            for te, be in exit_data.iterrows():
                print(f"  {te.time()}: H:{be['high']:.2f} L:{be['low']:.2f} C:{be['close']:.2f}")
                if is_long:
                    if be['low'] <= sl: print("  >> HIT STOP LOSS"); break
                    if be['high'] >= tp: print("  >> HIT TAKE PROFIT"); break
                else:
                    if be['high'] >= sl: print("  >> HIT STOP LOSS"); break
                    if be['low'] <= tp: print("  >> HIT TAKE PROFIT"); break
            break
