import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load optimized trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_optimized_trades.csv')
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

# Create Figure
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=("Optimized Equity Curve (Long Only + EMA200)", "Strategy Drawdown (USD)"))

fig.add_trace(go.Scatter(x=df['date'], y=df['cum_pnl'], name='Optimized Equity', line=dict(color='#fbbf24', width=3)), row=1, col=1)
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NQ ORB 30m 戰略優化版儀表板</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: flex-end; }}
        .header h1 {{ margin: 0; color: #fbbf24; }}
        .badge {{ background: #fbbf24; color: #020617; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
        .card h2 {{ margin: 0 0 15px 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; }}
        .stats-row {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
        .stats-val {{ font-size: 22px; font-weight: 700; color: #f8fafc; }}
        .highlight {{ color: #fbbf24; }}
        #chart {{ background: #0f172a; border-radius: 12px; padding: 15px; border: 1px solid #334155; }}
        .filter-summary {{ background: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #3b82f6; }}
        .filter-summary ul {{ margin: 10px 0 0 20px; color: #94a3b8; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>NQ 30m ORB 戰略優化版 <span class="badge">OPTIMIZED</span></h1>
                <div style="color: #64748b; margin-top: 5px;">基於 DataBento 數據與趨勢過濾</div>
            </div>
            <div style="color: #64748b;">更新日期: 2026-05-13</div>
        </div>

        <div class="filter-summary">
            <strong>⚙️ 優化邏輯：</strong>
            <ul>
                <li><strong>純多頭 (Long Only)</strong>：剔除長期表現不佳的空單。</li>
                <li><strong>趨勢過濾 (200 EMA)</strong>：僅在日線處於多頭排列時進場，減少盤整市的磨損。</li>
                <li><strong>盈虧比 (RR 1.5)</strong>：擴大每筆獲利潛力，更適配 NQ 的趨勢特性。</li>
            </ul>
        </div>

        <div class="grid">
            <div class="card">
                <h2>優化後總收益 (PnL)</h2>
                <div class="stats-val highlight">{total_stats['pnl']}</div>
            </div>
            <div class="card">
                <h2>勝率 (Win Rate)</h2>
                <div class="stats-val">{total_stats['win_rate']}</div>
            </div>
            <div class="card">
                <h2>最大回撤 (Max DD)</h2>
                <div class="stats-val" style="color:#ef4444;">{total_stats['max_dd']}</div>
            </div>
            <div class="card">
                <h2>交易次數 (Trades)</h2>
                <div class="stats-val">{total_stats['trades']}</div>
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

with open(r'C:\Users\user\.gemini\antigravity\scratch\nq_optimized_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Optimized dashboard saved.")
