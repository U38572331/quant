import pandas as pd
import plotly.graph_objects as go
import os

RESULTS_CSV = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\vwap_retest_raw_results.csv"
OUT_HTML = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\equity_curve.html"

# Load data
df = pd.read_csv(RESULTS_CSV)
df['Date'] = pd.to_datetime(df['Date'])
df.sort_values('Date', inplace=True)

fig = go.Figure()

# Plot equity curve for different TP_Sizes to see overall stability
for tp_val in df['TP_Size'].unique():
    subset = df[df['TP_Size'] == tp_val].copy()
    subset['Cum_PnL'] = subset['PnL'].cumsum()
    
    fig.add_trace(go.Scatter(
        x=subset['Date'],
        y=subset['Cum_PnL'],
        mode='lines',
        name=f"TP Size: {tp_val}x"
    ))

fig.update_layout(
    title="Cumulative PnL (Equity Curve) - 5m Breakout + RTH VWAP Retest",
    xaxis_title="Date",
    yaxis_title="Cumulative Points (NQ)",
    template="plotly_dark",
    hovermode='x unified'
)

fig.write_html(OUT_HTML)
print(f"Equity curve saved to {OUT_HTML}")
