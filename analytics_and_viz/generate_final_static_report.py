import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

# 1. Load Data
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_trades_5m_fixed.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').drop_duplicates('date')

# 2. Calculate Cumulative R
df['cum_r'] = df['pnl_r'].cumsum()
df_long = df[df['type'] == 'Long'].copy()
df_short = df[df['type'] == 'Short'].copy()
df_long['cum_r'] = df_long['pnl_r'].cumsum()
df_short['cum_r'] = df_short['pnl_r'].cumsum()

# 3. Generate Static Plots (The "Wiggly" Charts)
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# Top Plot: Total Equity
ax1.plot(df['date'], df['cum_r'], color='#fbbf24', linewidth=2, label='Total Strategy R')
ax1.set_title(f'Total Strategy Equity (Net: {df["pnl_r"].sum():.2f} R)', fontsize=14, pad=15)
ax1.grid(True, alpha=0.2)
ax1.legend()

# Bottom Plot: Long vs Short
ax2.plot(df_long['date'], df_long['cum_r'], color='#34d399', linewidth=1.5, label='Long Only')
ax2.plot(df_short['date'], df_short['cum_r'], color='#f87171', linewidth=1.5, label='Short Only')
ax2.set_title('Long vs Short Performance Comparison', fontsize=14, pad=15)
ax2.grid(True, alpha=0.2)
ax2.legend()

plt.tight_layout()
plot_path = r'C:\Users\user\.gemini\antigravity\scratch\nq_final_static_plot.png'
plt.savefig(plot_path, dpi=150)

# 4. Generate Monthly Heatmap
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
monthly_r = df.groupby(['year', 'month'])['pnl_r'].sum().unstack().fillna(0)

plt.figure(figsize=(12, 6))
sns.heatmap(monthly_r, annot=True, fmt=".1f", cmap='RdYlGn', center=0, cbar_kws={'label': 'Monthly R'})
plt.title('Monthly Profit Matrix (R-Units)')
heatmap_path = r'C:\Users\user\.gemini\antigravity\scratch\nq_final_heatmap.png'
plt.savefig(heatmap_path, dpi=150)

# 5. HTML Dashboard
total_r = df['pnl_r'].sum()
win_rate = (df['pnl_r'] > 0).mean() * 100

html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NQ 30m ORB 最終審定版 (RTH Only)</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #020617; color: #f8fafc; padding: 30px; line-height: 1.6; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ color: #fbbf24; border-bottom: 2px solid #1e293b; padding-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
        .card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; text-align: center; }}
        .card h3 {{ margin: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; }}
        .card .val {{ font-size: 36px; font-weight: 800; color: #fbbf24; margin-top: 10px; }}
        .chart-section {{ background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 30px; }}
        img {{ max-width: 100%; border-radius: 8px; }}
        .rule-tag {{ background: #1e293b; padding: 5px 12px; border-radius: 20px; font-size: 13px; color: #3b82f6; border: 1px solid #3b82f6; margin-right: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NQ 30m ORB 最終審定報告 <span style="font-size: 16px; color: #64748b; font-weight: normal;">(2020 - 2026)</span></h1>
        
        <div style="margin: 20px 0;">
            <span class="rule-tag">RTH Session Only</span>
            <span class="rule-tag">5m Confirmation</span>
            <span class="rule-tag">Risk Standardized (R)</span>
        </div>

        <div class="stats">
            <div class="card"><h3>累積獲利</h3><div class="val">{total_r:.2f} R</div></div>
            <div class="card"><h3>勝率</h3><div class="val">{win_rate:.2f}%</div></div>
            <div class="card"><h3>交易天數</h3><div class="val">{len(df)} 天</div></div>
        </div>

        <div class="chart-section">
            <h2 style="margin-top:0;">策略資產曲線 (真實波動)</h2>
            <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_final_static_plot.png">
        </div>

        <div class="chart-section">
            <h2 style="margin-top:0;">月度損益矩陣 (Heatmap)</h2>
            <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_final_heatmap.png">
        </div>
        
        <div style="color: #64748b; font-size: 12px; text-align: center; margin-top: 50px;">
            數據來源: DataBento Institution Grade Feed | 回測模型: 5m Confirmation V2.1
        </div>
    </div>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_master_report.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("Final Static Report Generated Successfully.")
