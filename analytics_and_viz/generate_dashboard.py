import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_30m_fixed.csv')
df['exit_time'] = pd.to_datetime(df['exit_time'], utc=True).dt.tz_convert('America/New_York')
df['cum_pnl'] = df['pnl'].cumsum()
df['peak'] = df['cum_pnl'].cummax()
df['drawdown'] = df['cum_pnl'] - df['peak']

# Stats function
def get_stats(data):
    if len(data) == 0: return {}
    wins = data[data['pnl'] > 0]
    losses = data[data['pnl'] < 0]
    win_rate = len(wins) / len(data) * 100
    total_pnl = data['pnl'].sum()
    pf = wins['pnl'].sum() / abs(losses['pnl'].sum()) if len(losses) > 0 else np.inf
    avg_pnl = data['pnl'].mean()
    return {
        'trades': len(data),
        'win_rate': f"{win_rate:.1f}%",
        'pnl': f"{total_pnl:,.2f}",
        'pf': f"{pf:.2f}",
        'avg': f"{avg_pnl:.2f}"
    }

total_stats = get_stats(df)
long_stats = get_stats(df[df['type'] == 'Long'])
short_stats = get_stats(df[df['type'] == 'Short'])

# Create Figure
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=("Cumulative Equity (Points)", "Strategy Drawdown (Points)"))

# Equity
fig.add_trace(go.Scatter(x=df['exit_time'], y=df['cum_pnl'], name='Total Equity', line=dict(color='#00d2ff', width=2)), row=1, col=1)
# Drawdown
fig.add_trace(go.Scatter(x=df['exit_time'], y=df['drawdown'], name='Drawdown', fill='tozeroy', line=dict(color='#ff4b2b', width=1)), row=2, col=1)

fig.update_layout(template="plotly_dark", height=800, showlegend=False,
                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

chart_json = fig.to_json()

# HTML Template
html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NQ ORB 30m 策略儀表板</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            background: linear-gradient(to right, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid #334155;
        }}
        .card h2 {{
            margin: 0 0 15px 0;
            font-size: 14px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stats-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .stats-val {{
            font-size: 20px;
            font-weight: 700;
        }}
        .positive {{ color: #10b981; }}
        .negative {{ color: #ef4444; }}
        #chart {{
            background: #1e293b;
            border-radius: 12px;
            padding: 10px;
            border: 1px solid #334155;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #64748b;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NQ 30m ORB 策略專業分析</h1>
            <div style="font-size: 14px; color: #94a3b8;">數據區間: 2010 - 2026</div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>總體表現 (Total)</h2>
                <div class="stats-row"><span>總盈虧</span><span class="stats-val positive">{total_stats['pnl']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{total_stats['win_rate']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{total_stats['pf']}</span></div>
                <div class="stats-row"><span>交易次數</span><span class="stats-val">{total_stats['trades']}</span></div>
            </div>
            <div class="card">
                <h2>多單表現 (Long)</h2>
                <div class="stats-row"><span>總盈虧</span><span class="stats-val positive">{long_stats['pnl']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{long_stats['win_rate']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{long_stats['pf']}</span></div>
                <div class="stats-row"><span>交易次數</span><span class="stats-val">{long_stats['trades']}</span></div>
            </div>
            <div class="card">
                <h2>空單表現 (Short)</h2>
                <div class="stats-row"><span>總盈虧</span><span class="stats-val positive">{short_stats['pnl']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{short_stats['win_rate']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{short_stats['pf']}</span></div>
                <div class="stats-row"><span>交易次數</span><span class="stats-val">{short_stats['trades']}</span></div>
            </div>
        </div>

        <div id="chart"></div>

        <div class="footer">
            分析日期: 2026-05-13 | 本報告由 Antigravity 策略引擎生成
        </div>
    </div>

    <script>
        const chartData = {chart_json};
        Plotly.newPlot('chart', chartData.data, chartData.layout);
    </script>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_strategy_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Professional dashboard saved to nq_strategy_dashboard.html")
