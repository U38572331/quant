import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time, timedelta

# 1. GENERATE CLEAN DATA (Front-Month Filtered)
print("Regenerating Master Results...")
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')

# Filter for NQ, exclude MNQ and spreads
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-', na=False)]
df = df[~df['symbol'].str.startswith('MNQ')]

# Keep Front Month per minute
df = df.sort_values(['ts_event', 'volume'], ascending=[True, False])
df = df.groupby(df.index).first()

df = df[df.index >= '2020-01-01'].copy()
df['date'] = df.index.date

# VWAP Levels
levels = {}
for date, day in df.groupby('date'):
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth['close'] * rth['volume']).sum() / rth['volume'].sum() if not rth.empty and rth['volume'].sum() > 0 else np.nan
    eth = day[day.index.time < time(9,30)]
    eth_v = (eth['close'] * eth['volume']).sum() / eth['volume'].sum() if not eth.empty and eth['volume'].sum() > 0 else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v}

# Backtest
trades = []
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
            if is_long and not (entry > y_rth and entry > c_eth): break
            if is_short and not (entry < y_rth and entry < c_eth): break
            
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
            
            trades.append({'date': curr_d, 'type': 'Long' if is_long else 'Short', 'pnl': max(-1.0, min(1.0, pnl))})
            break

final_df = pd.DataFrame(trades)
final_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_master_results.csv', index=False)

# 2. GENERATE ULTIMATE DASHBOARD
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 20))

# Curves
ax1 = plt.subplot2grid((4, 2), (0, 0), colspan=2)
final_df['cum_r'] = final_df['pnl'].cumsum()
final_df_l = final_df[final_df['type'] == 'Long'].copy()
final_df_s = final_df[final_df['type'] == 'Short'].copy()
final_df_l['cum_r'] = final_df_l['pnl'].cumsum()
final_df_s['cum_r'] = final_df_s['pnl'].cumsum()

ax1.plot(final_df['date'], final_df['cum_r'], color='#fbbf24', linewidth=3, label='Total Strategy')
ax1.plot(final_df_l['date'], final_df_l['cum_r'], color='#34d399', alpha=0.6, label='Long Only')
ax1.plot(final_df_s['date'], final_df_s['cum_r'], color='#f87171', alpha=0.6, label='Short Only')
ax1.set_title('Final Corrected Master Equity Curves', fontsize=16)
ax1.legend()

# Monte Carlo
ax2 = plt.subplot2grid((4, 2), (1, 0), colspan=2)
results = final_df['pnl'].values
sim_paths = [np.cumsum(np.random.choice(results, size=len(results), replace=True)) for _ in range(1000)]
sim_paths = np.array(sim_paths)
x = np.arange(len(results))
ax2.plot(x, np.percentile(sim_paths, 50, axis=0), color='#fbbf24')
ax2.fill_between(x, np.percentile(sim_paths, 5, axis=0), np.percentile(sim_paths, 95, axis=0), color='#fbbf24', alpha=0.1)
ax2.set_title('Monte Carlo Projections (1000 Runs)', fontsize=14)

# DD & WR
ax3 = plt.subplot2grid((4, 2), (2, 0))
dds = [np.min(p - np.maximum.accumulate(p)) for p in sim_paths]
ax3.hist(dds, bins=30, color='#3b82f6', alpha=0.7)
ax3.set_title('Max Drawdown Distribution')

ax4 = plt.subplot2grid((4, 2), (2, 1))
wr_l = (final_df_l['pnl'] > 0).mean() * 100
wr_s = (final_df_s['pnl'] > 0).mean() * 100
ax4.bar(['Long', 'Short'], [wr_l, wr_s], color=['#34d399', '#f87171'])
ax4.set_title('Win Rate by Direction (%)')

# Heatmap
ax5 = plt.subplot2grid((4, 2), (3, 0), colspan=2)
final_df['date'] = pd.to_datetime(final_df['date'])
final_df['year'] = final_df['date'].dt.year
final_df['month'] = final_df['date'].dt.month
monthly = final_df.groupby(['year', 'month'])['pnl'].sum().unstack().fillna(0)
sns.heatmap(monthly, annot=True, fmt=".1f", cmap='RdYlGn', center=0, ax=ax5)
ax5.set_title('Monthly Performance (R-Units)')

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_ultimate_master_plot_v2.png', dpi=150)

# HTML
wr = (final_df['pnl'] > 0).mean() * 100
total = final_df['pnl'].sum()
html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
.card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; }}
.val {{ font-size: 32px; font-weight: bold; color: #fbbf24; }}
img {{ max-width: 100%; border-radius: 8px; border: 1px solid #1e293b; }}
</style></head><body>
<h1>NQ ORB 終極全方位圖表 (修正版)</h1>
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-bottom:20px;">
    <div class="card"><div>總累積獲利</div><div class="val">+{total:.1f} R</div></div>
    <div class="card"><div>綜合勝率</div><div class="val" style="color:#34d399;">{wr:.1f}%</div></div>
    <div class="card"><div>交易樣本數</div><div class="val">{len(final_df)}</div></div>
</div>
<div class="card"><h2>全方位數據與風險分析看板</h2><img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_ultimate_master_plot_v2.png"></div>
</body></html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_ultimate_master_dashboard_v2.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Master Calibration Complete.")
