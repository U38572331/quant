import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load clean R-unit trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_clean_trades_r.csv')
df['date'] = pd.to_datetime(df['date'])

# Separate Long and Short
df_long = df[df['type'] == 'Long'].copy()
df_short = df[df['type'] == 'Short'].copy()

df['cum_r'] = df['pnl_r'].cumsum()
df_long['cum_r'] = df_long['pnl_r'].cumsum()
df_short['cum_r'] = df_short['pnl_r'].cumsum()

# Stats
def get_stats(data):
    if len(data) == 0: return {}
    wins = data[data['pnl_r'] > 0]
    win_rate = len(wins) / len(data) * 100
    total_r = data['pnl_r'].sum()
    return {
        'trades': len(data),
        'win_rate': f"{win_rate:.2f}%",
        'r_gain': f"{total_r:,.2f} R"
    }

total_stats = get_stats(df)
long_stats = get_stats(df_long)
short_stats = get_stats(df_short)

# Create Figure
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.1, 
                    subplot_titles=("Strategy Performance (Risk Standardized - R)", "Long vs Short Performance Comparison"))

# Subplot 1: Total Equity
fig.add_trace(go.Scatter(x=df['date'], y=df['cum_r'], name='Total Equity (R)', line=dict(color='#fbbf24', width=3)), row=1, col=1)

# Subplot 2: Long vs Short
fig.add_trace(go.Scatter(x=df_long['date'], y=df_long['cum_r'], name='Long Only (R)', line=dict(color='#34d399', width=2)), row=2, col=1)
fig.add_trace(go.Scatter(x=df_short['date'], y=df_short['cum_r'], name='Short Only (R)', line=dict(color='#f87171', width=2)), row=2, col=1)

fig.update_layout(template="plotly_dark", height=800, 
                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

chart_json = fig.to_json()

# HTML Template
html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NQ 30m ORB 最終審定版儀表板 (風險標準化)</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background: #020617; color: #f8fafc; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #1e293b; }}
        .val {{ font-size: 24px; font-weight: bold; color: #fbbf24; }}
        .sub {{ color: #94a3b8; font-size: 14px; margin-top: 5px; }}
    </style>
</head>
<body>
    <h1>NQ 30m ORB 最終審定版儀表板 (風險標準化 R)</h1>
    <div style="margin-bottom:20px; color:#94a3b8;">數據源: DataBento (DBN) | 策略: 原始 Long/Short | 盈虧比: 1:1</div>
    
    <div class="grid">
        <div class="card">
            <h2>總體獲利 (Total)</h2>
            <div class="val">{total_stats['r_gain']}</div>
            <div class="sub">勝率: {total_stats['win_rate']}</div>
        </div>
        <div class="card">
            <h2>多單表現 (Long)</h2>
            <div class="val" style="color:#34d399;">{long_stats['r_gain']}</div>
            <div class="sub">勝率: {long_stats['win_rate']}</div>
        </div>
        <div class="card">
            <h2>空單表現 (Short)</h2>
            <div class="val" style="color:#f87171;">{short_stats['r_gain']}</div>
            <div class="sub">勝率: {short_stats['win_rate']}</div>
        </div>
    </div>
    
    <div id="chart"></div>
    <script>
        const data = {chart_json};
        Plotly.newPlot('chart', data.data, data.layout);
    </script>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_clean_r_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print("Clean R-unit dashboard saved.")
