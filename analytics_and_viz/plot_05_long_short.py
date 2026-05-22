import pandas as pd
import plotly.graph_objects as go

RESULTS_CSV = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\vwap_retest_raw_results.csv"
OUT_HTML = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\equity_curve_0.5_long_short.html"

df = pd.read_csv(RESULTS_CSV)
df['Date'] = pd.to_datetime(df['Date'])
df.sort_values('Date', inplace=True)

df_opt = df[df['TP_Size'] == 0.5].copy()

longs = df_opt[df_opt['Direction'] == 'Long'].copy()
shorts = df_opt[df_opt['Direction'] == 'Short'].copy()

longs['Cum_PnL'] = longs['PnL'].cumsum()
shorts['Cum_PnL'] = shorts['PnL'].cumsum()
df_opt['Total_Cum_PnL'] = df_opt['PnL'].cumsum()

win_l = len(longs[longs['PnL'] > 0]) / len(longs) if len(longs) > 0 else 0
win_s = len(shorts[shorts['PnL'] > 0]) / len(shorts) if len(shorts) > 0 else 0
pnl_l = longs['PnL'].sum()
pnl_s = shorts['PnL'].sum()

print(f"Long  Trades: {len(longs)}, WinRate: {win_l:.1%}, Total PnL: {pnl_l:.1f} pts")
print(f"Short Trades: {len(shorts)}, WinRate: {win_s:.1%}, Total PnL: {pnl_s:.1f} pts")
print(f"Total Trades: {len(df_opt)}, Total PnL: {df_opt['PnL'].sum():.1f} pts")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=longs['Date'], y=longs['Cum_PnL'],
    mode='lines', name='🔵 Long 做多',
    line=dict(color='#00e676', width=2)
))
fig.add_trace(go.Scatter(
    x=shorts['Date'], y=shorts['Cum_PnL'],
    mode='lines', name='🔴 Short 做空',
    line=dict(color='#f44336', width=2)
))
fig.add_trace(go.Scatter(
    x=df_opt['Date'], y=df_opt['Total_Cum_PnL'],
    mode='lines', name='⚪ Total',
    line=dict(color='#ffffff', width=3, dash='dash')
))

fig.update_layout(
    title=f"做多 vs 做空 | TP = 0.5x (0.5 倍 ORB Range)<br>"
          f"Long 勝率: {win_l:.1%} ({pnl_l:.0f} pts) | Short 勝率: {win_s:.1%} ({pnl_s:.0f} pts)",
    xaxis_title="Date",
    yaxis_title="Cumulative Points (NQ)",
    template="plotly_dark",
    hovermode='x unified',
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
)

fig.write_html(OUT_HTML)
print("Done:", OUT_HTML)
