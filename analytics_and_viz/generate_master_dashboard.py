import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load master trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_master_trades.csv')
df['date'] = pd.to_datetime(df['date'])
df['cum_pnl'] = df['pnl_usd'].cumsum()
df['peak'] = df['cum_pnl'].cummax()
df['drawdown'] = df['cum_pnl'] - df['peak']

# Stats function
def get_stats(data):
    if len(data) == 0: return {}
    wins = data[data['pnl_usd'] > 0]
    losses = data[data['pnl_usd'] < 0]
    win_rate = len(wins) / len(data) * 100
    total_pnl = data['pnl_usd'].sum()
    pf = wins['pnl_usd'].sum() / abs(losses['pnl_usd'].sum()) if len(losses) > 0 else np.inf
    return {
        'trades': len(data),
        'win_rate': f"{win_rate:.1f}%",
        'pnl': f"${total_pnl:,.2f}",
        'pf': f"{pf:.2f}",
        'max_dd': f"${data['drawdown'].min():,.2f}"
    }

total_stats = get_stats(df)
long_stats = get_stats(df[df['type'] == 'Long'])
short_stats = get_stats(df[df['type'] == 'Short'])

# Create Figure
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=("Master Strategy Equity (USD)", "Strategy Drawdown (USD)"))

fig.add_trace(go.Scatter(x=df['date'], y=df['cum_pnl'], name='Equity', line=dict(color='#2ecc71', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['date'], y=df['drawdown'], name='Drawdown', fill='tozeroy', line=dict(color='#e74c3c', width=1)), row=2, col=1)

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
    <title>NQ 30m ORB 最終審定版儀表板</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: flex-end; }}
        .header h1 {{ margin: 0; color: #10b981; }}
        .badge {{ background: #10b981; color: #020617; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
        .card h2 {{ margin: 0 0 15px 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; }}
        .stats-row {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
        .stats-val {{ font-size: 22px; font-weight: 700; }}
        .pos {{ color: #10b981; }}
        .neg {{ color: #ef4444; }}
        #chart {{ background: #0f172a; border-radius: 12px; padding: 15px; border: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>NQ 30m ORB 最終審定版儀表板 <span class="badge">LEAN ENGINE LOGIC</span></h1>
                <div style="color: #64748b; margin-top: 5px;">數據源: DataBento DBN (GLBX MDP3)</div>
            </div>
            <div style="color: #64748b;">最後更新: 2026-05-13</div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>總體核心指標 (Total)</h2>
                <div class="stats-row"><span>淨損益 (USD)</span><span class="stats-val pos">{total_stats['pnl']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{total_stats['win_rate']}</span></div>
                <div class="stats-row"><span>最大回撤</span><span class="stats-val neg">{total_stats['max_dd']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{total_stats['pf']}</span></div>
            </div>
            <div class="card">
                <h2>多單表現 (Long)</h2>
                <div class="stats-row"><span>淨損益 (USD)</span><span class="stats-val pos">{long_stats['pnl']}</span></div>
                <div class="stats-row"><span>勝率</span><span class="stats-val">{long_stats['win_rate']}</span></div>
                <div class="stats-row"><span>獲利因子</span><span class="stats-val">{long_stats['pf']}</span></div>
            </div>
            <div class="card">
                <h2>空單表現 (Short)</h2>
                <div class="stats-row"><span>淨損益 (USD)</span><span class="stats-val">{short_stats['pnl']}</span></div>
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

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_master_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Final Master Dashboard saved.")
