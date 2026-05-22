import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

trades_file = 'kalman_orb_trades.csv'
if not os.path.exists(trades_file):
    print(f"Error: {trades_file} not found.")
    exit(1)

df = pd.read_csv(trades_file)

if len(df) == 0:
    print("No trades found.")
    exit(1)

# Ensure datetime index
df['Exit_Time'] = pd.to_datetime(df['Exit_Time'], utc=True)
df = df.set_index('Exit_Time')

# Basic Metrics
total_trades = len(df)
wins = df[df['PnL'] > 0]
losses = df[df['PnL'] <= 0]
win_rate = len(wins) / total_trades
total_pnl = df['PnL'].sum()
avg_pnl = df['PnL'].mean()

avg_win = wins['PnL'].mean() if len(wins) > 0 else 0
avg_loss = losses['PnL'].mean() if len(losses) > 0 else 0
sum_win = wins['PnL'].sum()
sum_loss = abs(losses['PnL'].sum())
profit_factor = (sum_win / sum_loss) if sum_loss != 0 else float('inf')

# Expectancy
expectancy = avg_pnl # avg PnL is the mathematical expectancy

# Cumulative PnL and Drawdown
df['Cum_PnL'] = df['PnL'].cumsum()
df['Peak'] = df['Cum_PnL'].cummax()
df['Drawdown'] = df['Cum_PnL'] - df['Peak']
max_drawdown = df['Drawdown'].min()

# Daily Returns for Sharpe/Sortino
daily_pnl = df['PnL'].resample('D').sum().dropna()
daily_pnl = daily_pnl[daily_pnl != 0] # exclude days without trades if they snuck in
mean_daily = daily_pnl.mean()
std_daily = daily_pnl.std()

sharpe_ratio = (mean_daily / std_daily) * np.sqrt(252) if std_daily > 0 else 0

downside_returns = daily_pnl[daily_pnl < 0]
sortino_ratio = (mean_daily / downside_returns.std()) * np.sqrt(252) if len(downside_returns)>0 and downside_returns.std() > 0 else 0

print("--- PROFESSIONAL QUANTITATIVE METRICS ---")
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate*100:.2f}%")
print(f"Total PnL: {total_pnl:.2f} Points (approx ${total_pnl*20:,.2f})")
print(f"Profit Factor: {profit_factor:.2f}")
print(f"Expectancy: {expectancy:.2f} Points/Trade")
print(f"Average Win: {avg_win:.2f} Points")
print(f"Average Loss: {avg_loss:.2f} Points")
print(f"Max Drawdown: {max_drawdown:.2f} Points (approx ${max_drawdown*20:,.2f})")
print(f"Sharpe Ratio (Annualized): {sharpe_ratio:.2f}")
print(f"Sortino Ratio (Annualized): {sortino_ratio:.2f}")

# Monthly Returns visualization
monthly_pnl = df['PnL'].resample('M').sum()
monthly_pnl.index = monthly_pnl.index.strftime('%Y-%m')

# Visualizations
fig = make_subplots(
    rows=3, cols=1, 
    shared_xaxes=False,
    vertical_spacing=0.1,
    subplot_titles=('Cumulative PnL (Equity Curve)', 'Drawdown Curve', 'Monthly PnL Histogram'),
    row_heights=[0.5, 0.25, 0.25]
)

# 1. Equity Curve
fig.add_trace(go.Scatter(x=df.index, y=df['Cum_PnL'], name='Cumulative PnL', line=dict(color='cyan', width=2), fill='tozeroy'), row=1, col=1)

# 2. Drawdown
fig.add_trace(go.Scatter(x=df.index, y=df['Drawdown'], name='Drawdown', line=dict(color='red', width=1), fill='tozeroy'), row=2, col=1)

# 3. Monthly PnL
colors = ['#00FF00' if val > 0 else '#FF0000' for val in monthly_pnl.values]
fig.add_trace(go.Bar(x=monthly_pnl.index, y=monthly_pnl.values, name='Monthly PnL', marker_color=colors), row=3, col=1)

fig.update_layout(
    height=1200, 
    template='plotly_dark', 
    title='Professional Quantitative Report - Kalman 15m ORB Strategy',
    showlegend=False
)

report_file = 'kalman_quant_report.html'
fig.write_html(report_file)
print(f"Dashboard saved to {os.path.abspath(report_file)}")

with open('quant_metrics.txt', 'w') as f:
    f.write(f"Total Trades|{total_trades}\n")
    f.write(f"Win Rate|{win_rate*100:.2f}%\n")
    f.write(f"Profit Factor|{profit_factor:.2f}\n")
    f.write(f"Expectancy|{expectancy:.2f} Points\n")
    f.write(f"Max Drawdown|{max_drawdown:.2f} Points\n")
    f.write(f"Sharpe Ratio|{sharpe_ratio:.2f}\n")
    f.write(f"Sortino Ratio|{sortino_ratio:.2f}\n")
