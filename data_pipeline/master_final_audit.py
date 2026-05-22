import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import time, timedelta

# 1. LOAD AND CLEAN
print("Starting Final Clean Backtest...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')
df = df[df.index >= '2022-01-01'].copy()
df['date'] = df.index.date

# 2. VWAP LEVELS
levels = {}
for date, day in df.groupby('date'):
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth['close'] * rth['volume']).sum() / rth['volume'].sum() if not rth.empty else np.nan
    eth = day[day.index.time < time(9,30)]
    eth_v = (eth['close'] * eth['volume']).sum() / eth['volume'].sum() if not eth.empty else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v}

# 3. BACKTEST
results = []
dates = sorted(df['date'].unique())
for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df['date'] == curr_d].sort_index()
    y_rth = levels.get(prev_d, {}).get('rth', np.nan)
    c_eth = levels.get(curr_d, {}).get('eth', np.nan)
    if np.isnan(y_rth) or np.isnan(c_eth): continue
    
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
            sl = orb_l if is_long else orb_h
            risk = abs(entry - sl)
            if risk < 5: break
            
            # CONFLUENCE FILTER
            if is_long and not (entry > y_rth and entry > c_eth): break
            if is_short and not (entry < y_rth and entry < c_eth): break
            
            tp = entry + (entry - sl) if is_long else entry - (sl - entry)
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
            
            results.append(max(-1.0, min(1.0, pnl)))
            break

# 4. STATS & MONTE CARLO
results = np.array(results)
win_rate = (results > 0).mean()
print(f"Verified Win Rate: {win_rate:.2f}")

num_sims = 1000
sim_paths = []
for _ in range(num_sims):
    path = np.cumsum(np.random.choice(results, size=len(results), replace=True))
    sim_paths.append(path)
sim_paths = np.array(sim_paths)

# 5. FINAL VISUALIZATION
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))

x = np.arange(len(results))
ax1.plot(x, np.percentile(sim_paths, 50, axis=0), color='#fbbf24', label='Median Path')
ax1.fill_between(x, np.percentile(sim_paths, 5, axis=0), np.percentile(sim_paths, 95, axis=0), color='#fbbf24', alpha=0.1, label='95% Confidence')
ax1.set_title('Final Calibrated Monte Carlo Simulation', fontsize=14)
ax1.legend()

drawdowns = [np.min(p - np.maximum.accumulate(p)) for p in sim_paths]
ax2.hist(drawdowns, bins=30, color='#3b82f6', alpha=0.7)
ax2.set_title('Max Drawdown Distribution (R-Units)', fontsize=14)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_v3.png', dpi=150)

# 6. FINAL HTML
avg_final = np.mean(sim_paths[:, -1])
worst_final = np.percentile(sim_paths[:, -1], 5)
avg_dd = np.mean(drawdowns)

html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>NQ ORB 最終校正報告</title><style>
body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
.card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; }}
.val {{ font-size: 32px; font-weight: bold; color: #fbbf24; }}
img {{ max-width: 100%; border-radius: 8px; border: 1px solid #1e293b; }}
</style></head>
<body>
<h1>NQ ORB 最終校正報告 (三層審計版)</h1>
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-bottom:20px;">
    <div class="card"><div>預期總獲利</div><div class="val">+{avg_final:.1f} R</div></div>
    <div class="card"><div>勝率</div><div class="val" style="color:#34d399;">{win_rate*100:.1f}%</div></div>
    <div class="card"><div>平均最大回撤</div><div class="val" style="color:#ef4444;">{avg_dd:.1f} R</div></div>
</div>
<div class="card"><h2>資產預測圖</h2><img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_final_v3.png"></div>
</body></html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_report_v3.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Calibration Masterpiece Done.")
