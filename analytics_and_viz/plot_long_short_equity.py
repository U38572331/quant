import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

RESULTS_CSV = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\vwap_retest_raw_results.csv"
OUT_HTML = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\equity_curve_long_short.html"

# Load data
df = pd.read_csv(RESULTS_CSV)
df['Date'] = pd.to_datetime(df['Date'])
df.sort_values('Date', inplace=True)

# Select the most profitable TP_Size to keep the chart clean
opt_tp = 2.0
df_opt = df[df['TP_Size'] == opt_tp].copy()

# Filter Longs and Shorts
longs = df_opt[df_opt['Direction'] == 'Long'].copy()
shorts = df_opt[df_opt['Direction'] == 'Short'].copy()

# Cumulative sums
longs['Cum_PnL'] = longs['PnL'].cumsum()
shorts['Cum_PnL'] = shorts['PnL'].cumsum()
df_opt['Total_Cum_PnL'] = df_opt['PnL'].cumsum()

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=longs['Date'], y=longs['Cum_PnL'],
    mode='lines', name='🔵 Long (做多) PnL',
    line=dict(color='#00e676', width=2)
))

fig.add_trace(go.Scatter(
    x=shorts['Date'], y=shorts['Cum_PnL'],
    mode='lines', name='🔴 Short (做空) PnL',
    line=dict(color='#f44336', width=2)
))

fig.add_trace(go.Scatter(
    x=df_opt['Date'], y=df_opt['Total_Cum_PnL'],
    mode='lines', name='⚪ Total (總和) PnL',
    line=dict(color='#ffffff', width=3, dash='dash')
))

# Calculate Win Rates
win_l = len(longs[longs['PnL'] > 0]) / len(longs) if len(longs)>0 else 0
win_s = len(shorts[shorts['PnL'] > 0]) / len(shorts) if len(shorts)>0 else 0

title_str = (
    f"做多 vs 做空 績效切割 (TP = {opt_tp}x)<br>"
    f"Long 勝率: {win_l:.1%} | Short 勝率: {win_s:.1%}"
)

fig.update_layout(
    title=title_str,
    xaxis_title="Date",
    yaxis_title="Cumulative Points (NQ)",
    template="plotly_dark",
    hovermode='x unified',
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
)

fig.write_html(OUT_HTML)
print(f"Equity curve saved to {OUT_HTML}")
