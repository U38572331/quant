import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load raw trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_trades.csv')
df['date'] = pd.to_datetime(df['date'])
df['cum_pts'] = df['pnl_pts'].cumsum()
df['peak'] = df['cum_pts'].cummax()
df['drawdown'] = df['cum_pts'] - df['peak']

# Stats function
def get_stats(data):
    if len(data) == 0: return {}
    wins = data[data['pnl_pts'] > 0]
    losses = data[data['pnl_pts'] < 0]
    win_rate = len(wins) / len(data) * 100
    total_pts = data['pnl_pts'].sum()
    pf = wins['pnl_pts'].sum() / abs(losses['pnl_pts'].sum()) if len(losses) > 0 else np.inf
    return {
        'trades': len(data),
        'win_rate': f"{win_rate:.2f}%",
        'pts': f"{total_pts:,.2f} pts",
        'pf': f"{pf:.2f}",
        'max_dd': f"{data['drawdown'].min():,.2f} pts"
    }

total_stats = get_stats(df)
long_stats = get_stats(df[df['type'] == 'Long'])
short_stats = get_stats(df[df['type'] == 'Short'])

# Create Figure
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=("Cumulative Points (Raw)", "Drawdown (Points)"))

fig.add_trace(go.Scatter(x=df['date'], y=df['cum_pts'], name='Raw Points', line=dict(color='#3b82f6', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['drawdown'], name='Drawdown', fill='tozeroy', line=dict(color='#ef4444', width=1)), row=2, col=1)

fig.update_layout(template="plotly_dark", height=800, showlegend=False,
                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

chart_json = fig.to_json()

# HTML Template
html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NQ 30m ORB 原始純點數儀表板</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background: #020617; color: #f8fafc; padding: 20px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #1e293b; }}
        .val {{ font-size: 24px; font-weight: bold; color: #3b82f6; }}
    </style>
</head>
<body>
    <h1>NQ 30m ORB 原始純點數回測 (無損耗)</h1>
    <div class="grid">
        <div class="card"><h2>總收益 (Points)</h2><div class="val">{total_stats['pts']}</div></div>
        <div class="card"><h2>勝率</h2><div class="val">{total_stats['win_rate']}</div></div>
        <div class="card"><h2>最大回撤 (Points)</h2><div class="val">{total_stats['max_dd']}</div></div>
    </div>
    <div id="chart"></div>
    <script>
        const data = {chart_json};
        Plotly.newPlot('chart', data.data, data.layout);
    </script>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
