import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Load the Optimized V3 Data
# (I'll re-run the core logic to get separate series)
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_master_results.csv')
# Wait, the above CSV might not have the 4 features. 
# I'll re-calculate from the combination mining result which is already saved.
df_mining = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_extended_vwap_mining.csv')

# Apply V3 Rules
df_long = df_mining[(df_mining['type'] == 'Long') & 
                    (df_mining['c_rth'] == 1) & (df_mining['c_eth'] == 1) & 
                    (df_mining['y_rth'] == 1) & (df_mining['y_eth'] == 1)].copy()

df_short = df_mining[(df_mining['type'] == 'Short') & 
                     (df_mining['c_rth'] == 0) & (df_mining['c_eth'] == 0) & 
                     (df_mining['y_rth'] == 1) & (df_mining['y_eth'] == 1)].copy()

# Calculate Metrics
def get_metrics(df_side):
    if len(df_side) == 0: return 0, 0, 0
    wr = (df_side['pnl'] > 0).mean() * 100
    total_r = df_side['pnl'].sum()
    cum_r = df_side['pnl'].cumsum()
    max_dd = (cum_r - cum_r.cummax()).min()
    return wr, total_r, max_dd

wr_l, r_l, dd_l = get_metrics(df_long)
wr_s, r_s, dd_s = get_metrics(df_short)

# 2. Visualization
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

# Long Curve
ax1.plot(df_long['pnl'].cumsum().values, color='#34d399', linewidth=3, label=f'Long (1,1,1,1) | WR: {wr_l:.1f}%')
ax1.set_title(f'V3 Optimized LONG Performance (+{r_l:.1f} R)', fontsize=14)
ax1.set_ylabel('R-Units')
ax1.legend()
ax1.grid(True, alpha=0.1)

# Short Curve
ax2.plot(df_short['pnl'].cumsum().values, color='#f87171', linewidth=3, label=f'Short (0,0,1,1) | WR: {wr_s:.1f}%')
ax2.set_title(f'V3 Optimized SHORT Performance (+{r_s:.1f} R)', fontsize=14)
ax2.set_ylabel('R-Units')
ax2.legend()
ax2.grid(True, alpha=0.1)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_v3_split_plot.png', dpi=150)

# 3. HTML Report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NQ ORB V3 多空拆分分析</title>
    <style>
        body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
        .split-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }}
        .card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; }}
        .long-val {{ color: #34d399; font-size: 32px; font-weight: bold; }}
        .short-val {{ color: #f87171; font-size: 32px; font-weight: bold; }}
        img {{ max-width: 100%; border-radius: 12px; border: 1px solid #1e293b; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>NQ ORB V3: 多空分開優化分析</h1>
    
    <div class="split-grid">
        <div class="card">
            <h2>多單優化 (All-Above)</h2>
            <p>規則：價格位於 4 條延伸線之上</p>
            <div class="long-val">+{r_l:.1f} R</div>
            <p>勝率：<b>{wr_l:.1f}%</b> | 最大回撤：{dd_l:.1f} R</p>
        </div>
        <div class="card">
            <h2>空單優化 (Value Rejection)</h2>
            <p>規則：今日跌破，昨日之上</p>
            <div class="short-val">+{r_s:.1f} R</div>
            <p>勝率：<b>{wr_s:.1f}%</b> | 最大回撤：{dd_s:.1f} R</p>
        </div>
    </div>

    <div class="card">
        <h2>多空分離資產曲線</h2>
        <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_v3_split_plot.png">
    </div>
</body>
</html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_v3_split_report.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("V3 Split Analysis Generated.")
