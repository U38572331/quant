import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Load data
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_rr_sensitivity_data.csv')

def analyze_rr(side_df):
    stats = []
    for rr in side_df['rr_target'].unique():
        sub = side_df[side_df['rr_target'] == rr]
        wr = (sub['pnl'] > 0).mean() * 100
        total_r = sub['pnl'].sum()
        
        gains = sub[sub['pnl'] > 0]['pnl'].sum()
        losses = abs(sub[sub['pnl'] < 0]['pnl'].sum())
        pf = gains / losses if losses > 0 else np.nan
        
        expectancy = sub['pnl'].mean()
        
        stats.append({'RR': rr, 'WinRate': wr, 'ProfitFactor': pf, 'Total_R': total_r, 'Expectancy': expectancy})
    return pd.DataFrame(stats).sort_values('RR')

long_rr = analyze_rr(df[df['type'] == 'Long'])
short_rr = analyze_rr(df[df['type'] == 'Short'])

# 2. Visualization
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

# Win Rate & Profit Factor for LONG
ax1.plot(long_rr['RR'], long_rr['WinRate'], color='#34d399', marker='o', label='Long WinRate (%)')
ax1_pf = ax1.twinx()
ax1_pf.plot(long_rr['RR'], long_rr['ProfitFactor'], color='#fbbf24', marker='s', label='Long Profit Factor')
ax1.set_title('LONG: Win Rate vs Profit Factor Across RRs', fontsize=14)
ax1.set_xlabel('Target RR Ratio')
ax1.set_ylabel('Win Rate %')
ax1_pf.set_ylabel('Profit Factor')
ax1.legend(loc='upper left')
ax1_pf.legend(loc='upper right')
ax1.grid(True, alpha=0.1)

# Win Rate & Profit Factor for SHORT
ax2.plot(short_rr['RR'], short_rr['WinRate'], color='#f87171', marker='o', label='Short WinRate (%)')
ax2_pf = ax2.twinx()
ax2_pf.plot(short_rr['RR'], short_rr['ProfitFactor'], color='#fbbf24', marker='s', label='Short Profit Factor')
ax2.set_title('SHORT: Win Rate vs Profit Factor Across RRs', fontsize=14)
ax2.set_xlabel('Target RR Ratio')
ax2.set_ylabel('Win Rate %')
ax2_pf.set_ylabel('Profit Factor')
ax2.legend(loc='upper left')
ax2_pf.legend(loc='upper right')
ax2.grid(True, alpha=0.1)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_rr_optimization_plot.png', dpi=150)

# 3. HTML Report
def format_table(df_stats):
    return df_stats.to_html(classes='table table-dark', index=False, float_format=lambda x: f'{x:.2f}')

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NQ ORB 多級損盈比優化矩陣</title>
    <style>
        body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
        .card {{ background: #0f172a; padding: 30px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 30px; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .table th, .table td {{ padding: 10px; border: 1px solid #1e293b; text-align: center; }}
        img {{ max-width: 100%; border-radius: 12px; }}
        .highlight {{ color: #fbbf24; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>NQ ORB: 多級損盈比 (RR) 優化矩陣</h1>
    
    <div class="card">
        <h2>多單 (Long) RR 戰力排行</h2>
        {format_table(long_rr)}
    </div>

    <div class="card">
        <h2>空單 (Short) RR 戰力排行</h2>
        {format_table(short_rr)}
    </div>

    <div class="card">
        <h2>RR 敏感度分析圖表 (勝率 vs 獲利因子)</h2>
        <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_rr_optimization_plot.png">
    </div>
</body>
</html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_rr_optimization_report.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("RR Optimization Report Generated.")
