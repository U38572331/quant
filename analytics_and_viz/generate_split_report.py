import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Load Data
raw = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_compare.csv')
opt = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_opt_compare.csv')
raw['date'] = pd.to_datetime(raw['date'])
opt['date'] = pd.to_datetime(opt['date'])

# 2. Split Data
raw_long = raw[raw['type'] == 'Long'].copy()
raw_short = raw[raw['type'] == 'Short'].copy()
opt_long = opt[opt['type'] == 'Long'].copy()
opt_short = opt[opt['type'] == 'Short'].copy()

# Cumulative sums
for d in [raw, opt, raw_long, raw_short, opt_long, opt_short]:
    d['cum_r'] = d['pnl_r'].cumsum()

# 3. Plotting: 3 Subplots
plt.style.use('dark_background')
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 18), sharex=True)

# Subplot 1: Total
ax1.plot(raw['date'], raw['cum_r'], color='#64748b', alpha=0.5, label='Original (Total)')
ax1.plot(opt['date'], opt['cum_r'], color='#fbbf24', linewidth=2, label='Optimized (Total)')
ax1.set_title('TOTAL Performance Comparison', fontsize=14)
ax1.legend()

# Subplot 2: Long
ax2.plot(raw_long['date'], raw_long['cum_r'], color='#64748b', alpha=0.5, label='Original (Long)')
ax2.plot(opt_long['date'], opt_long['cum_r'], color='#34d399', linewidth=2, label='Optimized (Long)')
ax2.set_title('LONG-ONLY Performance Comparison', fontsize=14)
ax2.legend()

# Subplot 3: Short
ax3.plot(raw_short['date'], raw_short['cum_r'], color='#64748b', alpha=0.5, label='Original (Short)')
ax3.plot(opt_short['date'], opt_short['cum_r'], color='#f87171', linewidth=2, label='Optimized (Short)')
ax3.set_title('SHORT-ONLY Performance Comparison', fontsize=14)
ax3.legend()

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_split_comparison_plot.png', dpi=150)

# 4. Stats Matrix
def stats(df):
    if len(df) == 0: return 0, 0, 0
    return (df['pnl_r'] > 0).mean()*100, df['pnl_r'].sum(), len(df)

r_l_wr, r_l_r, r_l_c = stats(raw_long)
o_l_wr, o_l_r, o_l_c = stats(opt_long)
r_s_wr, r_s_r, r_s_c = stats(raw_short)
o_s_wr, o_s_r, o_s_c = stats(opt_short)

# 5. HTML
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NQ ORB 多空拆分對比報告</title>
    <style>
        body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; }}
        .val {{ font-size: 28px; font-weight: bold; color: #fbbf24; }}
        img {{ max-width: 100%; border-radius: 12px; margin-top: 20px; }}
        h2 {{ color: #3b82f6; border-bottom: 1px solid #1e293b; padding-bottom: 10px; }}
    </style>
</head>
<body>
    <h1>NQ ORB 最終對比報告：多空拆分分析</h1>
    
    <h2>1. 多單對比 (Long Only)</h2>
    <div class="grid">
        <div class="card">
            <p>原始多單</p>
            <div class="val">{r_l_r:.1f} R</div>
            <p>勝率: {r_l_wr:.1f}% | 交易: {r_l_c}</p>
        </div>
        <div class="card" style="border-color: #34d399;">
            <p>優化後多單 (CLV > 0.6)</p>
            <div class="val" style="color: #34d399;">{o_l_r:.1f} R</div>
            <p>勝率: {o_l_wr:.1f}% | 交易: {o_l_c}</p>
        </div>
    </div>

    <h2>2. 空單對比 (Short Only)</h2>
    <div class="grid">
        <div class="card">
            <p>原始空單</p>
            <div class="val">{r_s_r:.1f} R</div>
            <p>勝率: {r_s_wr:.1f}% | 交易: {r_s_c}</p>
        </div>
        <div class="card" style="border-color: #f87171;">
            <p>優化後空單 (CLV < -0.6)</p>
            <div class="val" style="color: #f87171;">{o_s_r:.1f} R</div>
            <p>勝率: {o_s_wr:.1f}% | 交易: {o_s_c}</p>
        </div>
    </div>

    <div class="card">
        <h2>資產曲線全方位對比</h2>
        <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_split_comparison_plot.png">
    </div>
</body>
</html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_split_comparison_report.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Split comparison report generated.")
