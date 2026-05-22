import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load normalized trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_r.csv')
df['date'] = pd.to_datetime(df['date'])
df['cum_r'] = df['pnl_r'].cumsum()
df['peak'] = df['cum_r'].cummax()
df['drawdown'] = df['cum_r'] - df['peak']

# Stats function (using R units)
def get_stats(data):
    if len(data) == 0: return {}
    wins = data[data['pnl_r'] > 0]
    losses = data[data['pnl_r'] < 0]
    win_rate = len(wins) / len(data) * 100
    total_r = data['pnl_r'].sum()
    pf = wins['pnl_r'].sum() / abs(losses['pnl_r'].sum()) if len(losses) > 0 else np.inf
    return {
        'trades': len(data),
        'win_rate': f"{win_rate:.1f}%",
        'r_gain': f"{total_r:,.2f} R",
        'pf': f"{pf:.2f}",
        'max_dd': f"{data['drawdown'].min():.1f} R"
    }

total_stats = get_stats(df)
long_stats = get_stats(df[df['type'] == 'Long'])
short_stats = get_stats(df[df['type'] == 'Short'])

# Create Figure
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=("Strategy Equity (Risk Units - R)", "Strategy Drawdown (R)"))

fig.add_trace(go.Scatter(x=df['date'], y=df['cum_r'], name='Total Equity', line=dict(color='#34d399', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['drawdown'], name='Drawdown', fill='tozeroy', line=dict(color='#f87171', width=1)), row=2, col=1)

fig.update_layout(template="plotly_dark", height=800, showlegend=False,
                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

chart_json = fig.to_json()

# HTML Template (V2 - Normalized)
html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NQ ORB 30m 修正版儀表板 (風險標準化)</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #020617;
            color: #f8fafc;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #1e293b;
        }}
        .header h1 {{ margin: 0; color: #fbbf24; }}
        .alert {{
            background: #450a0a;
            border: 1px solid #991b1b;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
            color: #fecaca;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #0f172a;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }}
        .card h2 {{ margin: 0 0 15px 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; }}
        .stats-row {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
        .stats-val {{ font-size: 22px; font-weight: 700; color: #f8fafc; }}
        .highlight {{ color: #fbbf24; }}
        #chart {{ background: #0f172a; border-radius: 12px; padding: 15px; border: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NQ 30m ORB 修正版儀表板 <span style="font-size:16px; color:#94a3b8; font-weight:normal;">(風險標準化回測)</span></h1>
        </div>

        <div class="alert">
            <strong>⚠️ 數據修正通知：</strong> 此圖表已修正「點數價值不對等」問題。所有損益均以固定風險單位 (R) 計算，消除了 2024 年高點數價值對長期統計的干擾。
        </div>

        <div class="grid">
            <div class="card">
                <h2>總體指標 (Total)</h2>
                <div class="stats-row"><span>總收益 (R)</span><span class="stats-val highlight">{total_stats['r_gain']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{total_stats['win_rate']}</span></div>
                <div class="stats-row"><span>最大回撤</span><span class="stats-val" style="color:#ef4444;">{total_stats['max_dd']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{total_stats['pf']}</span></div>
            </div>
            <div class="card">
                <h2>多單 (Long Only)</h2>
                <div class="stats-row"><span>總收益 (R)</span><span class="stats-val">{long_stats['r_gain']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{long_stats['win_rate']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{long_stats['pf']}</span></div>
            </div>
            <div class="card">
                <h2>空單 (Short Only)</h2>
                <div class="stats-row"><span>總收益 (R)</span><span class="stats-val">{short_stats['r_gain']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{short_stats['win_rate']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{short_stats['pf']}</span></div>
            </div>
        </div>

        <div id="chart"></div>
    </div>

    <script>
        const chartData = {chart_json};
        Plotly.newPlot('chart', chartData.data, chartData.layout);
    </script>
</body>
</html>
"""

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_strategy_dashboard_v2.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("V2 Dashboard saved.")
