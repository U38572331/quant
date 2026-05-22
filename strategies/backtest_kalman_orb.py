import databento as db
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from tqdm import tqdm

data_file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

print("Loading data...")
store = db.DBNStore.from_file(data_file_path)
df = store.to_df()

if not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df.index)

print("Converting timezone to America/New_York (if UTC)...")
if df.index.tz is None:
    df.index = df.index.tz_localize('UTC')
df.index = df.index.tz_convert('America/New_York')

# Only keep RTH hours to save memory and processing time
df = df.between_time('09:30', '15:59')

print("Calculating Kalman Filter globally...")
# We must ensure data is sorted by time for Kalman Filter
df = df.sort_index()

sz = len(df)
prices = df['close'].values

Q = 1e-3  # process variance
R = 1e-1  # estimate of measurement variance

x_hat = np.zeros(sz)
P = np.zeros(sz)
x_hat_minus = np.zeros(sz)
P_minus = np.zeros(sz)
K = np.zeros(sz)

x_hat[0] = prices[0]
P[0] = 1.0

# Using numba or cython would be faster, but this loop should take a few seconds in basic Python for 1M rows
for k in tqdm(range(1, sz), desc="Kalman Filter"):
    x_hat_minus[k] = x_hat[k-1]
    P_minus[k] = P[k-1] + Q
    K[k] = P_minus[k] / (P_minus[k] + R)
    x_hat[k] = x_hat_minus[k] + K[k] * (prices[k] - x_hat_minus[k])
    P[k] = (1 - K[k]) * P_minus[k]

df['Kalman'] = x_hat
df['Kalman_Slope'] = df['Kalman'].diff()

print("Running backtest...")
trades = []

df_or_all = df.between_time('09:30', '09:34')
df_trade_all = df.between_time('09:35', '15:59')

grouped_or = df_or_all.groupby(df_or_all.index.date)
grouped_trade = df_trade_all.groupby(df_trade_all.index.date)

for date, trade_df in tqdm(grouped_trade, desc="Backtesting"):
    if date not in grouped_or.groups:
        continue
        
    or_df = grouped_or.get_group(date)
    if len(or_df) < 5: # Not enough 1m bars for OR
        continue
        
    or_high = or_df['high'].max()
    or_low = or_df['low'].min()
    
    in_trade = False
    breakout_occurred = False
    entry_price = 0
    trade_dir = 0 # 1 for long, -1 for short
    stop_loss = 0
    take_profit = 0
    entry_time = None
    
    for row in trade_df.itertuples():
        bar_time = row.Index
        close = row.close
        high = row.high
        low = row.low
        kalman_val = row.Kalman
        kalman_slope = row.Kalman_Slope
        
        # Check Entry
        if not in_trade and not breakout_occurred:
            # First candle to close outside OR
            if close > or_high:
                breakout_occurred = True
                if kalman_slope > 0:
                    in_trade = True
                    trade_dir = 1
                    entry_price = close
                    stop_loss = or_low
                    dist = entry_price - stop_loss
                    take_profit = entry_price + dist
                    entry_time = bar_time
                    if dist <= 0:
                        in_trade = False # Invalid
                    
            elif close < or_low:
                breakout_occurred = True
                if kalman_slope < 0:
                    in_trade = True
                    trade_dir = -1
                    entry_price = close
                    stop_loss = or_high
                    dist = stop_loss - entry_price
                    take_profit = entry_price - dist
                    entry_time = bar_time
                    if dist <= 0:
                        in_trade = False
                    
        # Check Exit
        if in_trade:
            # Skip intra-bar exits on the exact entry bar for simplicity
            if bar_time == entry_time:
                continue
                
            exit_price = None
            exit_reason = None
            
            if trade_dir == 1:
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif high >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
            elif trade_dir == -1:
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif low <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    
            # Session end force close
            if exit_price is None and bar_time.time() >= pd.Timestamp('15:59').time():
                exit_price = close
                exit_reason = 'Session_End'
                
            if exit_price is not None:
                pnl = (exit_price - entry_price) * trade_dir
                trades.append({
                    'Date': date,
                    'Entry_Time': entry_time,
                    'Exit_Time': bar_time,
                    'Direction': 'Long' if trade_dir == 1 else 'Short',
                    'Entry_Price': entry_price,
                    'Exit_Price': exit_price,
                    'Reason': exit_reason,
                    'PnL': pnl
                })
                in_trade = False
                break # Only 1 trade per session

df_trades = pd.DataFrame(trades)

if len(df_trades) == 0:
    print("No trades executed.")
else:
    df_trades['Cumulative_PnL'] = df_trades['PnL'].cumsum()
    print("\n--- Backtest Results ---")
    print(f"Total Trades: {len(df_trades)}")
    wins = df_trades[df_trades['PnL'] > 0]
    win_rate = len(wins) / len(df_trades) * 100
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL (Points): {df_trades['PnL'].sum():.2f}")
    avg_pnl = df_trades['PnL'].mean()
    print(f"Average PnL per Trade: {avg_pnl:.2f} Points")
    
    # Save Equity Curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_trades['Exit_Time'], y=df_trades['Cumulative_PnL'], mode='lines', name='Cumulative PnL (Points)', fill='tozeroy'))
    fig.update_layout(title='Kalman Filter 15m ORB Strategy Equity Curve', xaxis_title='Date', yaxis_title='PnL (Points)', template='plotly_dark')
    
    out_chart = 'kalman_orb_equity.html'
    fig.write_html(out_chart)
    print(f"Equity curve saved to {os.path.abspath(out_chart)}")
    df_trades.to_csv('kalman_orb_trades.csv', index=False)
