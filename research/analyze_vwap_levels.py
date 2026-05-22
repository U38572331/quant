import databento as db
import pandas as pd
import numpy as np
from datetime import time, timedelta

# 1. Load Data
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
df = df[df.index >= '2022-01-01'].copy()
df['date'] = df.index.date

# 2. VWAP Level Engine
def get_daily_levels(df):
    levels = {}
    for date, day in df.groupby('date'):
        rth = day[(day.index.time >= time(9, 30)) & (day.index.time <= time(16, 0))]
        rth_v = (rth['close'] * rth['volume']).sum() / rth['volume'].sum() if not rth.empty else np.nan
        eth = day[day.index.time < time(9, 30)]
        eth_v = (eth['close'] * eth['volume']).sum() / eth['volume'].sum() if not eth.empty else np.nan
        levels[date] = {'rth': rth_v, 'eth': eth_v}
    return levels

daily_levels = get_daily_levels(df)

# 3. Backtest
trades = []
dates = sorted(df['date'].unique())

for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df['date'] == curr_d].sort_index()
    y_rth = daily_levels.get(prev_d, {}).get('rth', np.nan)
    c_eth = daily_levels.get(curr_d, {}).get('eth', np.nan)
    if np.isnan(y_rth) or np.isnan(c_eth): continue
    
    orb_window = day[(day.index.time >= time(9, 30)) & (day.index.time <= time(10, 0))]
    if orb_window.empty: continue
    orb_h, orb_l = orb_window['high'].max(), orb_window['low'].min()
    if (orb_h - orb_l) < 5: continue
    
    trading = day[day.index.time > time(10, 0)]
    state = "IDLE"
    for t, bar in trading.iterrows():
        if t.time() > time(15, 50): break
        is_long = bar['close'] > orb_h
        is_short = bar['close'] < orb_l
        if is_long or is_short:
            entry = bar['close']
            sl = orb_l if is_long else orb_h
            risk = abs(entry - sl)
            tp = entry + (entry - sl) if is_long else entry - (sl - entry)
            
            pnl = -1.0
            exit_data = day[day.index > t]
            for te, be in exit_data.iterrows():
                if is_long:
                    if be['low'] <= sl: pnl = -1.0; break
                    elif be['high'] >= tp: pnl = 1.0; break
                    elif te.time() >= time(15, 55): pnl = (be['close'] - entry)/risk; break
                else:
                    if be['high'] >= sl: pnl = -1.0; break
                    elif be['low'] <= tp: pnl = 1.0; break
                    elif te.time() >= time(15, 55): pnl = (entry - be['close'])/risk; break
            
            pnl = max(-1.0, min(1.0, pnl)) # FINAL AUDIT CAP
            trades.append({
                'date': curr_d, 'type': 'Long' if is_long else 'Short', 'pnl': pnl,
                'above_y_rth': entry > y_rth, 'above_c_eth': entry > c_eth
            })
            state = "FINISHED"; break
    if state == "FINISHED": continue

pd.DataFrame(trades).to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_vwap_levels_results.csv', index=False)
print("FIXED VWAP Results generated.")
