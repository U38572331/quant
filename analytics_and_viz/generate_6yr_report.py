import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load 6-year trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_trades.csv')
df['date'] = pd.to_datetime(df['date'])
df['cum_r'] = df['pnl_r'].cumsum()

# 1. Monthly Heatmap
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
monthly_r = df.groupby(['year', 'month'])['pnl_r'].sum().unstack()

plt.figure(figsize=(12, 6))
sns.heatmap(monthly_r, annot=True, fmt=".1f", cmap='RdYlGn', center=0)
plt.title('Monthly R-unit PnL (2020-2026)')
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_heatmap.png')

# 2. Plotly Dashboard
df_long = df[df['type'] == 'Long'].copy()
df_short = df[df['type'] == 'Short'].copy()
df_long['cum_r'] = df_long['pnl_r'].cumsum()
df_short['cum_r'] = df_short['pnl_r'].cumsum()

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                    subplot_titles=("Total Strategy Equity (R)", "Long vs Short Comparison (R)"))

fig.add_trace(go.Scatter(x=df['date'], y=df['cum_r'], name='Total Equity', line=dict(color='#fbbf24', width=3)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_long['date'], y=df_long['cum_r'], name='Long Only', line=dict(color='#34d399')), row=2, col=1)
fig.add_trace(go.Scatter(x=df_short['date'], y=df_short['cum_r'], name='Short Only', line=dict(color='#f87171')), row=2, col=1)

fig.update_layout(template="plotly_dark", height=800, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
chart_json = fig.to_json()

# HTML
win_rate = (df['pnl_r'] > 0).mean() * 100
total_r = df['pnl_r'].sum()

html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NQ 30m ORB 最近六年回測報告 (2020-2026)</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background: #020617; color: #f8fafc; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .card {{ background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #1e293b; }}
        .val {{ font-size: 28px; font-weight: bold; color: #fbbf24; }}
    </style>
</head>
<body>
    <h1>NQ 30m ORB 最近六年回測報告 (2020-2026)</h1>
    <div class="grid">
        <div class="card"><h2>累積獲利 (R)</h2><div class="val">{total_r:,.2f} R</div></div>
        <div class="card"><h2>勝率</h2><div class="val">{win_rate:.2f}%</div></div>
        <div class="card"><h2>總交易次數</h2><div class="val">{len(df)}</div></div>
    </div>
    <div id="chart"></div>
    <div style="margin-top:30px;">
        <h2>月度損益矩陣 (Heatmap)</h2>
        <img src="file:///C:/Users/user/.gemini/antigravity/scratch/nq_6yr_heatmap.png" style="max-width:100%; border-radius:8px;">
    </div>
    <script>
        const data = {chart_json};
        Plotly.newPlot('chart', data.data, data.layout);
    </script>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("6-Year Analysis complete.")
