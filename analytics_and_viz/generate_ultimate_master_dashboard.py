import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load the most reliable data (Master Continuous Results)
# Since I didn't save the full 'results' to CSV in the previous step, I'll quickly re-generate them
# (I have the results in the environment, but to be safe I'll assume I need to reload)
# For efficiency, I'll use the 'nq_vwap_levels_results.csv' which I fixed earlier with CAP.

df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_vwap_levels_results.csv')
df['date'] = pd.to_datetime(df['date'])

# Only Optimized Trades (Confluence)
df_opt = df[((df['type'] == 'Long') & (df['above_y_rth'] == True) & (df['above_c_eth'] == True)) | 
            ((df['type'] == 'Short') & (df['above_y_rth'] == False) & (df['above_c_eth'] == False))].copy()

# 2. Split analysis
df_long = df_opt[df_opt['type'] == 'Long'].copy()
df_short = df_opt[df_opt['type'] == 'Short'].copy()

df_opt['cum_r'] = df_opt['pnl'].cumsum()
df_long['cum_r'] = df_long['pnl'].cumsum()
df_short['cum_r'] = df_short['pnl'].cumsum()

# 3. Create Master Visualization
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 20))

# Top: Multi-Curve
ax1 = plt.subplot2grid((4, 2), (0, 0), colspan=2)
ax1.plot(df_opt['date'], df_opt['cum_r'], color='#fbbf24', linewidth=3, label='Total Strategy')
ax1.plot(df_long['date'], df_long['cum_r'], color='#34d399', linewidth=1.5, label='Long Only', alpha=0.7)
ax1.plot(df_short['date'], df_short['cum_r'], color='#f87171', linewidth=1.5, label='Short Only', alpha=0.7)
ax1.set_title('Master Equity Curves (Long vs Short Breakdown)', fontsize=16)
ax1.legend()
ax1.grid(True, alpha=0.1)

# Middle Left: Monte Carlo
ax2 = plt.subplot2grid((4, 2), (1, 0), colspan=2)
results = df_opt['pnl'].values
num_sims = 1000
sim_paths = []
for _ in range(num_sims):
    sim_paths.append(np.cumsum(np.random.choice(results, size=len(results), replace=True)))
sim_paths = np.array(sim_paths)
x = np.arange(len(results))
ax2.plot(x, np.percentile(sim_paths, 50, axis=0), color='#fbbf24', label='Median Path')
ax2.fill_between(x, np.percentile(sim_paths, 5, axis=0), np.percentile(sim_paths, 95, axis=0), color='#fbbf24', alpha=0.1)
ax2.set_title('Monte Carlo Risk Projections (1000 Paths)', fontsize=14)
ax2.legend()

# Bottom Left: Drawdown
ax3 = plt.subplot2grid((4, 2), (2, 0))
drawdowns = [np.min(p - np.maximum.accumulate(p)) for p in sim_paths]
ax3.hist(drawdowns, bins=30, color='#3b82f6', alpha=0.7)
ax3.set_title('Max Drawdown Distribution', fontsize=14)

# Bottom Right: Win Rate by Type
ax4 = plt.subplot2grid((4, 2), (2, 1))
wr_l = (df_long['pnl'] > 0).mean() * 100
wr_s = (df_short['pnl'] > 0).mean() * 100
ax4.bar(['Long', 'Short'], [wr_l, wr_s], color=['#34d399', '#f87171'])
ax4.set_title('Win Rate by Direction (%)', fontsize=14)
ax4.set_ylim(0, 70)

# Heatmap at the bottom
ax5 = plt.subplot2grid((4, 2), (3, 0), colspan=2)
df_opt['year'] = df_opt['date'].dt.year
df_opt['month'] = df_opt['date'].dt.month
monthly = df_opt.groupby(['year', 'month'])['pnl'].sum().unstack().fillna(0)
sns.heatmap(monthly, annot=True, fmt=".1f", cmap='RdYlGn', center=0, ax=ax5)
ax5.set_title('Monthly Performance Matrix (R-Units)', fontsize=14)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_ultimate_master_plot.png', dpi=150)

# 4. Generate Master HTML
win_rate = (df_opt['pnl'] > 0).mean() * 100
total_r = df_opt['pnl'].sum()

html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NQ ORB 終極全方位圖表</title>
    <style>
        body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
        .header {{ border-bottom: 2px solid #fbbf24; padding-bottom: 10px; margin-bottom: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; text-align: center; }}
        .val {{ font-size: 32px; font-weight: bold; color: #fbbf24; }}
        img {{ max-width: 100%; border-radius: 12px; border: 1px solid #1e293b; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NQ ORB 策略全方位審定圖表 (2020-2026)</h1>
        <p>包含：多空拆分、蒙地卡羅、月度矩陣、回撤壓力測試</p>
    </div>

    <div class="stats">
        <div class="card"><div>累積獲利</div><div class="val">+{total_r:.1f} R</div></div>
        <div class="card"><div>綜合勝率</div><div class="val" style="color:#34d399;">{win_rate:.1f}%</div></div>
        <div class="card"><div>多單勝率</div><div class="val" style="color:#34d399;">{wr_l:.1f}%</div></div>
        <div class="card"><div>空單勝率</div><div class="val" style="color:#f87171;">{wr_s:.1f}%</div></div>
    </div>

    <div class="card">
        <h2>全方位數據看板</h2>
        <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_ultimate_master_plot.png">
    </div>
</body>
</html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_ultimate_master_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Ultimate Master Dashboard generated.")
