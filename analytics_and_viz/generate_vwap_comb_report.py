import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load data
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_extended_vwap_mining.csv')

# 2. Define Combination String
def get_comb(row):
    return f"CR:{row['c_rth']} CE:{row['c_eth']} YR:{row['y_rth']} YE:{row['y_eth']}"

df['comb'] = df.apply(get_comb, axis=1)

# 3. Analyze Separately for Long and Short
def analyze_side(side_df, title):
    stats = side_df.groupby('comb')['pnl'].agg(['count', 'mean', lambda x: (x > 0).mean()*100])
    stats.columns = ['Trades', 'Avg_R', 'Win_Rate']
    stats = stats[stats['Trades'] >= 10].sort_values('Win_Rate', ascending=False)
    return stats

long_stats = analyze_side(df[df['type'] == 'Long'], "Long")
short_stats = analyze_side(df[df['type'] == 'Short'], "Short")

# 4. Visualization: Top 5 Combinations for each
plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

sns.barplot(x=long_stats.head(10).index, y=long_stats.head(10)['Win_Rate'], ax=ax1, palette='Greens_r')
ax1.set_title('Top 10 VWAP Combinations for LONG Breakouts', fontsize=14)
ax1.set_ylim(40, 70)
ax1.axhline(55, color='white', linestyle='--', alpha=0.3)

sns.barplot(x=short_stats.head(10).index, y=short_stats.head(10)['Win_Rate'], ax=ax2, palette='Reds_r')
ax2.set_title('Top 10 VWAP Combinations for SHORT Breakouts', fontsize=14)
ax2.set_ylim(40, 70)
ax2.axhline(52, color='white', linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_vwap_comb_matrix.png', dpi=150)

# 5. HTML Report
def to_html_table(df):
    return df.head(10).to_html(classes='table table-dark')

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NQ ORB VWAP 全組合戰力矩陣</title>
    <style>
        body {{ background: #020617; color: #f8fafc; font-family: sans-serif; padding: 40px; }}
        .card {{ background: #0f172a; padding: 30px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 30px; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .table th, .table td {{ padding: 12px; border: 1px solid #1e293b; text-align: center; }}
        .highlight {{ color: #34d399; font-weight: bold; }}
        img {{ max-width: 100%; border-radius: 12px; }}
        .legend {{ font-size: 13px; color: #94a3b8; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>NQ ORB: 4-VWAP 全組合戰力矩陣 (2021-2026)</h1>
    <div class="legend">
        <b>CR</b>: Current RTH VWAP | <b>CE</b>: Current ETH VWAP | <b>YR</b>: Yesterday RTH VWAP | <b>YE</b>: Yesterday ETH VWAP <br>
        (1 = 價格在其上方, 0 = 價格在其下方)
    </div>

    <div class="card">
        <h2>多單 (Long) 戰力排行 TOP 10</h2>
        {to_html_table(long_stats)}
    </div>

    <div class="card">
        <h2>空單 (Short) 戰力排行 TOP 10</h2>
        {to_html_table(short_stats)}
    </div>

    <div class="card">
        <h2>全組合勝率對比圖</h2>
        <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_vwap_comb_matrix.png">
    </div>
</body>
</html>
"""
with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_vwap_comb_report.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("VWAP Combination Matrix Report Generated.")
