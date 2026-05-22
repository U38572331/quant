import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time, timedelta

# 1. DATA INGESTION (ES 10-YEAR FILE)
print("Processing 10-Year ES (S&P 500) Audit (2016-2026)...")
path = r"C:\Users\user\Downloads\GLBX-20260503-3DDYMET438\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn"
data = db.DBNStore.from_file(path)
df = data.to_df()
df.index = pd.to_datetime(df.index).tz_convert('America/New_York')

# Filter for ES only
df = df[df['symbol'].str.startswith('ES') & ~df['symbol'].str.contains('-', na=False)]
df = df[~df['symbol'].str.startswith('MES')] # Exclude Micros

# Keep Front Month per minute
df = df.sort_values(['ts_event', 'volume'], ascending=[True, False]).groupby(df.index).first()

df['date'] = df.index.date
df['pv'] = df['close'] * df['volume']

# VWAP Levels Cache
levels = {}
for date, day in df.groupby('date'):
    rth = day[(day.index.time >= time(9,30)) & (day.index.time <= time(16,0))]
    rth_v = (rth['pv'].sum() / rth['volume'].sum()) if not rth.empty else np.nan
    eth_v = (day['pv'].sum() / day['volume'].sum()) if not day.empty else np.nan
    levels[date] = {'rth': rth_v, 'eth': eth_v}

# 2. V4 PRO ENGINE
trades = []
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
        is_long, is_short = bar['close'] > orb_h, bar['close'] < orb_l
        if is_long or is_short:
            entry = bar['close']
            c_rth_df = day[(day.index.time >= time(9,30)) & (day.index <= t)]
            c_rth = c_rth_df['pv'].sum() / c_rth_df['volume'].sum()
            c_eth_df = day[day.index <= t]
            c_eth = c_eth_df['pv'].sum() / c_eth_df['volume'].sum()
            
            # V4 FILTERS
            if is_long:
                if not (entry > c_rth and entry > c_eth and entry > y_rth and entry > y_eth): break
                rr = 1.3
            else:
                if not (entry < c_rth and entry < c_eth and entry > y_rth and entry > y_eth): break
                rr = 2.5
            
            sl = orb_l if is_long else orb_h
            risk = abs(entry - sl)
            if risk < 1: break # ES tick size is smaller, but 1 pt is still tiny
            tp = entry + rr * (entry - sl) if is_long else entry - rr * (sl - entry)
            
            pnl = -1.0
            exit_data = day[day.index > t]
            for te, be in exit_data.iterrows():
                if is_long:
                    if be['low'] <= sl: pnl = -1.0; break
                    elif be['high'] >= tp: pnl = rr; break
                    elif te.time() >= time(15,55): pnl = (be['close'] - entry)/risk; break
                else:
                    if be['high'] >= sl: pnl = -1.0; break
                    elif be['low'] <= tp: pnl = rr; break
                    elif te.time() >= time(15,55): pnl = (entry - be['close'])/risk; break
            trades.append({'date': curr_d, 'type': 'Long' if is_long else 'Short', 'pnl': pnl})
            break

final_df = pd.DataFrame(trades)

# 3. DASHBOARD
def get_stats(sub):
    if len(sub) == 0: return 0, 0, 0, 0
    wr = (sub['pnl'] > 0).mean() * 100
    total_r = sub['pnl'].sum()
    pf = sub[sub['pnl'] > 0]['pnl'].sum() / abs(sub[sub['pnl'] < 0]['pnl'].sum()) if sub[sub['pnl'] < 0]['pnl'].sum() != 0 else 0
    return wr, total_r, pf, len(sub)

wr_t, r_t, pf_t, cnt_t = get_stats(final_df)
wr_l, r_l, pf_l, cnt_l = get_stats(final_df[final_df['type'] == 'Long'])
wr_s, r_s, pf_s, cnt_s = get_stats(final_df[final_df['type'] == 'Short'])

plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 22))
ax1 = plt.subplot2grid((5, 2), (0, 0), colspan=2)
final_df['cum_r'] = final_df['pnl'].cumsum()
ax1.plot(final_df['date'], final_df['cum_r'], color='#a855f7', linewidth=4)
ax1.set_title(f'ES (S&P 500) 10-Year Master Equity Curve (+{r_t:.1f} R)', fontsize=16)

# Heatmap
final_df['date'] = pd.to_datetime(final_df['date'])
final_df['year'] = final_df['date'].dt.year
final_df['month'] = final_df['date'].dt.month
monthly = final_df.groupby(['year', 'month'])['pnl'].sum().unstack().fillna(0)
ax5 = plt.subplot2grid((5, 2), (3, 0), colspan=2)
sns.heatmap(monthly, annot=True, fmt=".1f", cmap='RdYlGn', center=0, ax=ax5)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\es_10yr_v4_plot.png', dpi=150)

html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
.card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }}
.val {{ font-size: 32px; font-weight: bold; color: #a855f7; }}
img {{ max-width: 100%; border-radius: 8px; border: 1px solid #1e293b; }}
</style></head><body>
<h1>ES (S&P 500) 10 年期跨品種審計報表 (2016-2026)</h1>
<div class="grid">
    <div class="card"><div>總累積獲利</div><div class="val">+{r_t:.1f} R</div></div>
    <div class="card"><div>綜合勝率</div><div class="val">{wr_t:.1f}%</div></div>
    <div class="card"><div>獲利因子 (PF)</div><div class="val">{pf_t:.2f}</div></div>
    <div class="card"><div>樣本總數</div><div class="val">{cnt_t}</div></div>
</div>
<div class="card"><h2>ES 10 年資產走勢與月度矩陣</h2><img src="file:///C:/Users/user/.gemini/antigravity/scratch/es_10yr_v4_plot.png"></div>
</body></html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\es_10yr_v4_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"ES 10-Year Audit Complete. Total R: +{r_t:.1f}")
