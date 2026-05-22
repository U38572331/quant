import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time, timedelta

# 1. DATA INGESTION (10-YEAR FILE)
print("Processing 10-Year Master Audit (2016-2026)...")
path = r"C:\Users\user\Downloads\GLBX-20260503-3DDYMET438\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')

# Filter for NQ, exclude MNQ and spreads
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-', na=False)]
df = df[~df['symbol'].str.startswith('MNQ')]

# Keep Front Month per minute
df = df.sort_values(['ts_event', 'volume'], ascending=[True, False])
df = df.groupby(df.index).first()

df['date'] = df.index.date
df['pv'] = df['close'] * df['volume']

# VWAP Levels Cache
print("Calculating 10 years of VWAP levels...")
levels = {}
for date, day in df.groupby('date'):
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth['pv'].sum() / rth['volume'].sum()) if not rth.empty else np.nan
    eth_v = (day['pv'].sum() / day['volume'].sum()) if not day.empty else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v}

# 2. V4 PRO BACKTEST ENGINE
trades = []
dates = sorted(df['date'].unique())
for i in range(1, len(dates)):
    curr_d, prev_d = dates[i], dates[i-1]
    day = df[df['date'] == curr_d].sort_index()
    y_rth, y_eth = levels.get(prev_d, {}).get('rth', np.nan), levels.get(prev_d, {}).get('eth', np.nan)
    if np.isnan(y_rth) or np.isnan(y_eth): continue
    
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
            c_rth_df = day[(day.index.time >= time(9,30)) & (day.index <= t)]
            c_rth = c_rth_df['pv'].sum() / c_rth_df['volume'].sum()
            c_eth_df = day[day.index <= t]
            c_eth = c_eth_df['pv'].sum() / c_eth_df['volume'].sum()
            
            if is_long:
                if not (entry > c_rth and entry > c_eth and entry > y_rth and entry > y_eth): break
                rr_target = 1.3
            else:
                if not (entry < c_rth and entry < c_eth and entry > y_rth and entry > y_eth): break
                rr_target = 2.5
            
            sl = orb_l if is_long else orb_h
            risk = abs(entry - sl)
            if risk < 5: break
            tp = entry + rr_target * (entry - sl) if is_long else entry - rr_target * (sl - entry)
            
            pnl = -1.0
            exit_data = day[day.index > t]
            for te, be in exit_data.iterrows():
                if is_long:
                    if be['low'] <= sl: pnl = -1.0; break
                    elif be['high'] >= tp: pnl = rr_target; break
                    elif te.time() >= time(15,55): pnl = (be['close'] - entry)/risk; break
                else:
                    if be['high'] >= sl: pnl = -1.0; break
                    elif be['low'] <= tp: pnl = rr_target; break
                    elif te.time() >= time(15,55): pnl = (entry - be['close'])/risk; break
            
            trades.append({'date': curr_d, 'type': 'Long' if is_long else 'Short', 'pnl': pnl})
            break

final_df = pd.DataFrame(trades)
final_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_10yr_v4_results.csv', index=False)

# 3. GENERATE 10-YEAR DASHBOARD
def get_stats(sub):
    if len(sub) == 0: return 0, 0, 0, 0
    wr = (sub['pnl'] > 0).mean() * 100
    total_r = sub['pnl'].sum()
    pf = sub[sub['pnl'] > 0]['pnl'].sum() / abs(sub[sub['pnl'] < 0]['pnl'].sum()) if sub[sub['pnl'] < 0]['pnl'].sum() != 0 else 0
    return wr, total_r, pf, len(sub)

wr_l, r_l, pf_l, cnt_l = get_stats(final_df[final_df['type'] == 'Long'])
wr_s, r_s, pf_s, cnt_s = get_stats(final_df[final_df['type'] == 'Short'])
wr_total, r_total, pf_total, cnt_total = get_stats(final_df)

plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 22))

ax1 = plt.subplot2grid((5, 2), (0, 0), colspan=2)
final_df['cum_r'] = final_df['pnl'].cumsum()
ax1.plot(final_df['date'], final_df['cum_r'], color='#3b82f6', linewidth=4, label='V4 Pro 10-Year')
ax1.set_title(f'10-Year Master Equity Curve (+{r_total:.1f} R)', fontsize=16)
ax1.legend()

ax2 = plt.subplot2grid((5, 2), (1, 0), colspan=2)
results = final_df['pnl'].values
sim_paths = np.array([np.cumsum(np.random.choice(results, size=len(results), replace=True)) for _ in range(1000)])
ax2.plot(np.arange(len(results)), np.percentile(sim_paths, 50, axis=0), color='#fbbf24')
ax2.fill_between(np.arange(len(results)), np.percentile(sim_paths, 5, axis=0), np.percentile(sim_paths, 95, axis=0), color='#fbbf24', alpha=0.1)
ax2.set_title('Monte Carlo 10-Year Stress Test', fontsize=14)

ax5 = plt.subplot2grid((5, 2), (3, 0), colspan=2)
final_df['date'] = pd.to_datetime(final_df['date'])
final_df['year'] = final_df['date'].dt.year
final_df['month'] = final_df['date'].dt.month
monthly = final_df.groupby(['year', 'month'])['pnl'].sum().unstack().fillna(0)
sns.heatmap(monthly, annot=True, fmt=".1f", cmap='RdYlGn', center=0, ax=ax5)
ax5.set_title('10-Year Monthly Performance (R-Units)')

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_10yr_v4_plot.png', dpi=150)

html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
.card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }}
.val {{ font-size: 32px; font-weight: bold; color: #fbbf24; }}
.long-val {{ color: #34d399; font-size: 28px; font-weight: bold; }}
.short-val {{ color: #f87171; font-size: 28px; font-weight: bold; }}
.sub {{ color: #94a3b8; font-size: 13px; }}
img {{ max-width: 100%; border-radius: 8px; border: 1px solid #1e293b; }}
</style></head><body>
<h1>NQ ORB 10 年期大審計報表 (2016-2026)</h1>
<div class="grid">
    <div class="card"><div>總累積獲利</div><div class="val">+{r_total:.1f} R</div></div>
    <div class="card"><div>綜合勝率</div><div class="val" style="color:#34d399;">{wr_total:.1f}%</div></div>
    <div class="card"><div>獲利因子 (PF)</div><div class="val">{pf_total:.2f}</div></div>
    <div class="card"><div>樣本總數</div><div class="val">{cnt_total}</div></div>
</div>
<div class="grid">
    <div class="card"><h2>🟢 多單 (1.3R)</h2><div class="long-val">+{r_l:.1f} R</div><div class="sub">勝率：{wr_l:.1f}% | PF：{pf_l:.2f}</div></div>
    <div class="card"><h2>🔴 空單 (2.5R)</h2><div class="short-val">+{r_s:.1f} R</div><div class="sub">勝率：{wr_s:.1f}% | PF：{pf_s:.2f}</div></div>
</div>
<div class="card"><h2>10 年期資產走勢與月度矩陣</h2><img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_10yr_v4_plot.png"></div>
</body></html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_10yr_v4_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"10-Year V4 Audit Complete. Total R: +{r_total:.1f}")
