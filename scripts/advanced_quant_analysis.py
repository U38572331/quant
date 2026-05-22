import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def generate_advanced_report():
    trades_path = "backtest_trades.csv"
    if not os.path.exists(trades_path):
        print("Trades file not found.")
        return
        
    df = pd.read_csv(trades_path)
    # Ensure UTC awareness for all datetime conversions to avoid mixed types
    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    df['EntryTime'] = pd.to_datetime(df['EntryTime'], utc=True)
    df['ExitTime'] = pd.to_datetime(df['ExitTime'], utc=True)
    df['PnL'] = pd.to_numeric(df['PnL'])
    df = df.sort_values('Date')
    
    # Duration Calculation
    # Using .total_seconds() via map if .dt fails for some reason, though .dt should work on timedelta
    diff = df['ExitTime'] - df['EntryTime']
    df['Duration'] = diff.map(lambda x: x.total_seconds() / 60.0 if pd.notnull(x) else 0)
    
    # Monte Carlo (1000 Runs)
    n_sims = 1000
    pnl_array = df['PnL'].values
    mc_results = []
    for _ in range(n_sims):
        shuffled = np.random.choice(pnl_array, size=len(pnl_array), replace=True)
        mc_results.append(np.cumsum(shuffled))
    
    mc_results = np.array(mc_results)
    mc_percentiles = np.percentile(mc_results, [5, 50, 95], axis=0)
    
    # Visuals
    fig = make_subplots(
        rows=4, cols=2,
        subplot_titles=(
            "Monte Carlo Equity Stress Test (1000 Runs)", "Cumulative PnL (Standard Sequence)",
            "Probability of PnL Out-Performance", "Drawdown Magnitude Distribution",
            "Win/Loss Duration Comparison (Minutes)", "Profit Contribution by Day of Week",
            "Rolling Sharpe Ratio (20-Trade Window)", "Consecutive Win/Loss Streaks"
        ),
        vertical_spacing=0.08, horizontal_spacing=0.1,
        specs=[[{"colspan": 2}, None], [{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "xy"}]]
    )
    
    steps = np.arange(len(pnl_array))
    fig.add_trace(go.Scatter(x=steps, y=mc_percentiles[1], name="Median MC", line=dict(color="#00ff88")), row=1, col=1)
    fig.add_trace(go.Scatter(x=steps, y=mc_percentiles[0], name="5th Percentile (Stress)", line=dict(color="#ff4d4d", dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=steps, y=mc_percentiles[2], name="95th Percentile (Optimal)", line=dict(color="#00aaff", dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=steps, y=df['PnL'].cumsum().values, name="Actual Path", line=dict(color="white", width=3)), row=1, col=1)

    fig.add_trace(go.Box(y=df[df['PnL'] > 0]['Duration'], name="Win Duration", marker_color="#00ff88"), row=3, col=1)
    fig.add_trace(go.Box(y=df[df['PnL'] <= 0]['Duration'], name="Loss Duration", marker_color="#ff4d4d"), row=3, col=1)

    df['DayOfWeek'] = df['Date'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_pnl = df.groupby('DayOfWeek')['PnL'].sum().reindex(day_order).fillna(0)
    fig.add_trace(go.Bar(x=day_pnl.index, y=day_pnl.values, marker_color='#3498db'), row=3, col=2)

    rolling_mean = df['PnL'].rolling(20).mean()
    rolling_std = df['PnL'].rolling(20).std()
    rolling_sharpe = (rolling_mean / rolling_std).fillna(0)
    fig.add_trace(go.Scatter(x=np.arange(len(df)), y=rolling_sharpe, name="Rolling Sharpe Scale", line=dict(color="#f1c40f")), row=4, col=1)

    peak = df['PnL'].cumsum().cummax()
    dd = (df['PnL'].cumsum() - peak)
    fig.add_trace(go.Histogram(x=dd, nbinsx=50, marker_color="#ff4d4d", name="DD Dist"), row=2, col=2)

    mc_ends = mc_results[:, -1]
    fig.add_trace(go.Histogram(x=mc_ends, nbinsx=30, cumulative_enabled=True, marker_color="#00ff88", name="MC CDF"), row=2, col=1)

    streaks = []
    curr = 0
    for p in df['PnL']:
        if p > 0:
            if curr >= 0: curr += 1
            else: streaks.append(curr); curr = 1
        else:
            if curr <= 0: curr -= 1
            else: streaks.append(curr); curr = -1
    streaks.append(curr)
    fig.add_trace(go.Histogram(x=streaks, marker_color="#9b59b6", name="Streaks"), row=4, col=2)

    fig.update_layout(height=1600, width=1200, template="plotly_dark", title_text="ADVANCED QUANTITATIVE STRESS TEST (V2)")
    
    report_path = r"C:\Users\user\.gemini\antigravity\brain\c31344a2-fc59-4a9d-bc24-28645bf47868\advanced_quant_report.html"
    fig.write_html(report_path)
    print(f"Report Generated: {report_path}")

if __name__ == "__main__":
    generate_advanced_report()
