import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Load Data
trades_path = r"C:\Users\user\backtest_trades.csv" # Main path from previous tools
if not os.path.exists(trades_path):
    trades_path = "backtest_trades.csv"

df = pd.read_csv(trades_path)
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')
df['CumPnL'] = df['PnL'].cumsum()

# Institutional Metrics Calculation
def calculate_metrics(pnl_series, dates):
    if len(pnl_series) == 0:
        return {k: 0 for k in ["Net PnL", "Win Rate", "Profit Factor", "Sharpe Ratio", "Sortino Ratio", "Expectancy", "Max Drawdown", "Recovery Factor", "Total Trades"]}
        
    total_net_pnl = pnl_series.sum()
    win_trades = pnl_series[pnl_series > 0]
    loss_trades = pnl_series[pnl_series <= 0]
    
    win_rate = len(win_trades) / len(pnl_series)
    avg_win = win_trades.mean() if len(win_trades) > 0 else 0
    avg_loss = abs(loss_trades.mean()) if len(loss_trades) > 0 else 0
    profit_factor = win_trades.sum() / abs(loss_trades.sum()) if abs(loss_trades.sum()) > 0 else np.inf
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    # Risk Metrics (Daily Returns approx)
    daily_pnl = pnl_series.groupby(dates.dt.date).sum()
    sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252) if daily_pnl.std() > 0 else 0
    
    negative_returns = daily_pnl[daily_pnl < 0]
    sortino = (daily_pnl.mean() / negative_returns.std()) * np.sqrt(252) if not negative_returns.empty and negative_returns.std() > 0 else np.inf
    
    # Drawdown
    cum_pnl = pnl_series.cumsum()
    peak = cum_pnl.cummax()
    drawdown = cum_pnl - peak
    max_dd = drawdown.min()
    recovery_factor = total_net_pnl / abs(max_dd) if abs(max_dd) > 0 else np.inf
    
    return {
        "Net PnL": total_net_pnl,
        "Win Rate": win_rate,
        "Profit Factor": profit_factor,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Expectancy": expectancy,
        "Max Drawdown": max_dd,
        "Recovery Factor": recovery_factor,
        "Total Trades": len(pnl_series)
    }

total_metrics = calculate_metrics(df['PnL'], df['Date'])
long_metrics = calculate_metrics(df[df['Type']=='Long']['PnL'], df[df['Type']=='Long']['Date'])
short_metrics = calculate_metrics(df[df['Type']=='Short']['PnL'], df[df['Type']=='Short']['Date'])

# Create Report Dashboard
fig = make_subplots(
    rows=4, cols=2,
    specs=[
        [{"colspan": 2, "type": "xy"}, None],         # Main Equity
        [{"type": "domain"}, {"type": "xy"}],         # Pie / Distribution
        [{"colspan": 2, "type": "xy"}, None],         # Heatmap (using heatmap trace in xy spec works)
        [{"type": "xy"}, {"type": "xy"}]              # Long vs Short / Drawdown
    ],
    subplot_titles=(
        "Portfolio Equity Growth (Institutional View)", 
        "Win/Loss Allocation", "Trade Expectancy Distribution",
        "Monthly Return Heatmap (Points)",
        "Strategy Attribution (Long vs Short)", "Drawdown Depth Over Time"
    ),
    vertical_spacing=0.08,
    horizontal_spacing=0.1
)

# 1. Equity Curves
fig.add_trace(go.Scatter(x=df['Date'], y=df['CumPnL'], name="Total Strategy", line=dict(color="#00ff88", width=3)), row=1, col=1)
fig.add_trace(go.Scatter(x=df[df['Type']=='Long']['Date'], y=df[df['Type']=='Long']['PnL'].cumsum(), name="Long Component", line=dict(color="#2980b9", dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=df[df['Type']=='Short']['Date'], y=df[df['Type']=='Short']['PnL'].cumsum(), name="Short Component", line=dict(color="#e74c3c", dash="dot")), row=1, col=1)

# 2. Results Allocation
fig.add_trace(go.Pie(labels=["Wins", "Losses"], values=[len(df[df['PnL']>0]), len(df[df['PnL']<=0])], marker=dict(colors=["#00ff88", "#ff4d4d"]), hole=0.5, name="Trade Results"), row=2, col=1)

# 3. PnL Distribution
fig.add_trace(go.Histogram(x=df['PnL'], nbinsx=100, marker_color='#9b59b6', name="Trade Dist"), row=2, col=2)

# 4. Monthly Heatmap
daily = df.groupby(df['Date'].dt.to_period('M'))['PnL'].sum().reset_index()
daily['Year'] = daily['Date'].dt.year
daily['Month'] = daily['Date'].dt.month
heatmap_data = daily.pivot(index='Year', columns='Month', values='PnL').fillna(0)

fig.add_trace(go.Heatmap(
    z=heatmap_data.values,
    x=[f"Month {m}" for m in heatmap_data.columns],
    y=heatmap_data.index,
    colorscale="RdYlGn",
    reversescale=False,
    zmid=0,
    showscale=True,
    colorbar=dict(title="Points")
), row=3, col=1)

# 5. Long vs Short Attribution
fig.add_trace(go.Bar(
    x=['Long', 'Short'], 
    y=[long_metrics['Net PnL'], short_metrics['Net PnL']],
    marker_color=['#2980b9', '#e74c3c'],
    name="Strategy Attribution"
), row=4, col=1)

# 6. Drawdown
peak = df['CumPnL'].cummax()
dd = df['CumPnL'] - peak
fig.add_trace(go.Scatter(x=df['Date'], y=dd, fill='tozeroy', line_color='#ff4d4d', name="Drawdown"), row=4, col=2)

# Global Layout Styling
fig.update_layout(
    template="plotly_dark",
    height=1400,
    width=1200,
    title=dict(text="NQ ORB + VWAP Institutional Performance Analytics", font=dict(size=24, color="#00ff88")),
    showlegend=True,
    paper_bgcolor="rgba(10,10,10,1)",
    plot_bgcolor="rgba(20,20,20,1)"
)

# Metrics Summary Div (to be included in HTML)
metrics_html = f"""
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #e0e0e0; padding: 30px; background: #0a0a0a; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px;">
    <h2 style="color: #00ff88; margin-top: 0; border-bottom: 1px solid #333; padding-bottom: 10px;">EXECUTIVE PERFORMANCE SUMMARY</h2>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">NET PROFIT</div>
            <div style="font-size: 20px; font-weight: bold; color: #00ff88;">{total_metrics['Net PnL']:,.2f} PTS</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">SHARPE RATIO</div>
            <div style="font-size: 20px; font-weight: bold;">{total_metrics['Sharpe Ratio']:.2f}</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">PROFIT FACTOR</div>
            <div style="font-size: 20px; font-weight: bold;">{total_metrics['Profit Factor']:.2f}</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">WIN RATE</div>
            <div style="font-size: 20px; font-weight: bold;">{total_metrics['Win Rate']:.2%}</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">MAX DRAWDOWN</div>
            <div style="font-size: 20px; font-weight: bold; color: #ff4d4d;">{total_metrics['Max Drawdown']:,.2f} PTS</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">SORTINO RATIO</div>
            <div style="font-size: 20px; font-weight: bold;">{total_metrics['Sortino Ratio']:.2f}</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">EXPECTANCY</div>
            <div style="font-size: 20px; font-weight: bold;">{total_metrics['Expectancy']:.2f} PTS</div>
        </div>
        <div style="padding: 15px; background: #1a1a1a; border-radius: 5px;">
            <div style="font-size: 12px; color: #888;">RECOVERY FACTOR</div>
            <div style="font-size: 20px; font-weight: bold;">{total_metrics['Recovery Factor']:.2f}</div>
        </div>
    </div>
</div>
"""

# Export Report
output_file = r"C:\Users\user\.gemini\antigravity\brain\c31344a2-fc59-4a9d-bc24-28645bf47868\professional_report.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("<html><body style='background:#0a0a0a; margin:0; padding:20px;'>")
    f.write(metrics_html)
    f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))
    f.write("</body></html>")

print(f"Institutional Report Generated: {output_file}")
