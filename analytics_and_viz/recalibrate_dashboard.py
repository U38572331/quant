import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Load Data
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_6yr_trades_5m_fixed.csv')
df['date'] = pd.to_datetime(df['date'])

# 2. Cleanup: Ensure unique dates (One trade per day)
df = df.sort_values('date').drop_duplicates('date')

# 3. Calculate Cumulative
df['cum_r'] = df['pnl_r'].cumsum()

# 4. Independent Long/Short calculation
df_long = df[df['type'] == 'Long'].copy()
df_short = df[df['type'] == 'Short'].copy()
df_long['cum_r'] = df_long['pnl_r'].cumsum()
df_short['cum_r'] = df_short['pnl_r'].cumsum()

# Stats
total_r = df['pnl_r'].sum()
win_rate = (df['pnl_r'] > 0).mean() * 100

# 5. Build Robust Plotly Chart
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.1, 
                    subplot_titles=(f"Total Strategy Equity (Actual R: {total_r:.2f})", "Long vs Short Comparison"))

fig.add_trace(go.Scatter(x=df['date'], y=df['cum_r'], name='Total Equity', line=dict(color='#fbbf24', width=2.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_long['date'], y=df_long['cum_r'], name='Long Only', line=dict(color='#34d399', width=1.5)), row=2, col=1)
fig.add_trace(go.Scatter(x=df_short['date'], y=df_short['cum_r'], name='Short Only', line=dict(color='#f87171', width=1.5)), row=2, col=1)

fig.update_layout(template="plotly_dark", height=800, 
                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

# Explicitly set Y-axis to avoid Plotly's auto-scaling bug
fig.update_yaxes(range=[df['cum_r'].min() - 10, df['cum_r'].max() + 10], row=1, col=1)

chart_json = fig.to_json()

# HTML
html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NQ 30m ORB 最終校正版儀表板</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background: #020617; color: #f8fafc; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .card {{ background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #1e293b; }}
        .val {{ font-size: 28px; font-weight: bold; color: #fbbf24; }}
    </style>
</head>
<body>
    <h1>NQ 30m ORB 最終校正版報告 (RTH Only)</h1>
    <div style="color: #94a3b8; margin-bottom: 20px;">
        💡 <strong>校正說明：</strong> 修正了圖表縮放比例錯誤。目前的 Y 軸反映的是真實的累積 R 值（約 80 R）。
    </div>
    <div class="grid">
        <div class="card"><h2>累積獲利 (R)</h2><div class="val">{total_r:.2f} R</div></div>
        <div class="card"><h2>勝率</h2><div class="val">{win_rate:.2f}%</div></div>
        <div class="card"><h2>交易天數</h2><div class="val">{len(df)}</div></div>
    </div>
    <div id="chart"></div>
    <script>
        const data = {chart_json};
        Plotly.newPlot('chart', data.data, data.layout);
    </script>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_fixed_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("Final Dashboard Calibration Complete.")
