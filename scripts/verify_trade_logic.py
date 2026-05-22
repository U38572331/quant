import pandas as pd
import plotly.graph_objects as go
from datetime import time

# 1. Verification: Pick a sample day
trades_df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_30m_fixed.csv')
sample_trade = trades_df.iloc[-5] # Pick a recent one
trade_date = sample_trade['date']
print(f"Verifying trade on {trade_date}")

# Load full data for that day
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
df = df.set_index('ts_event').tz_convert('America/New_York')
day_data = df[df.index.date == pd.to_datetime(trade_date).date()].copy()
# Filter for active symbol
active_sym = sample_trade['symbol']
day_data = day_data[day_data['symbol'] == active_sym]

# Filter for RTH
day_data = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time <= time(16, 0))]

# Calculate ORB for verification
orb_window = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time < time(10, 0))]
orb_h = orb_window['high'].max()
orb_l = orb_window['low'].min()

print(f"Calculated ORB: {orb_h} / {orb_l}")
print(f"Trade Data: Entry {sample_trade['entry_price']} at {sample_trade['entry_time']}")

# Create verification chart
fig = go.Figure(data=[go.Candlestick(x=day_data.index,
                open=day_data['open'],
                high=day_data['high'],
                low=day_data['low'],
                close=day_data['close'],
                name='NQ')])

# Add ORB lines
fig.add_hline(y=orb_h, line_dash="dash", line_color="green", annotation_text="ORB High")
fig.add_hline(y=orb_l, line_dash="dash", line_color="red", annotation_text="ORB Low")

# Add Trade Entry and Exit
fig.add_trace(go.Scatter(x=[sample_trade['entry_time']], y=[sample_trade['entry_price']],
                    mode='markers', marker=dict(size=12, symbol='triangle-up' if sample_trade['type'] == 'Long' else 'triangle-down', color='blue'),
                    name='Entry'))
fig.add_trace(go.Scatter(x=[sample_trade['exit_time']], y=[sample_trade['exit_price']],
                    mode='markers', marker=dict(size=12, symbol='x', color='black'),
                    name='Exit'))

fig.update_layout(title=f'Trade Verification: {trade_date} ({sample_trade["type"]})',
                  xaxis_title='Time', yaxis_title='Price',
                  height=600)

fig.write_html(r'C:\Users\user\.gemini\antigravity\scratch\trade_verification.html')
print("Verification chart saved to trade_verification.html")
