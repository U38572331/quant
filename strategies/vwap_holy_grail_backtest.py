import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Load data
file_path = r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet'
df = pd.read_parquet(file_path)

# Prepare datetime
df['ts_event'] = pd.to_datetime(df['ts_event'])
df.set_index('ts_event', inplace=True)
df.sort_index(inplace=True)

# Convert to Eastern Time for RTH filtering
df.index = df.index.tz_convert('US/Eastern')

# Filter for RTH (9:30 AM to 4:00 PM)
rth_df = df.between_time('09:30', '16:00').copy()

# Function to calculate daily anchored VWAP
def calculate_daily_vwap(group):
    # Typical price
    tp = (group['high'] + group['low'] + group['close']) / 3
    # Anchored VWAP
    group['my_vwap'] = (tp * group['volume']).cumsum() / group['volume'].cumsum()
    return group

print("Calculating Daily VWAP...")
rth_df = rth_df.groupby(rth_df.index.date, group_keys=False).apply(calculate_daily_vwap)

# Define Strategy: Always-in-the-market
# Start at 9:31 AM as per paper (first candle closes at 9:31)
rth_df['signal'] = np.where(rth_df['close'] > rth_df['my_vwap'], 1, -1)

# Shift signal by 1 minute to avoid look-ahead bias (enter at open of next minute)
rth_df['position'] = rth_df['signal'].shift(1)

# Calculate Returns
# Using log returns for simplicity of compounding
rth_df['pct_change'] = rth_df['close'].pct_change()
rth_df['strategy_ret'] = rth_df['position'] * rth_df['pct_change']

# Cumulative Returns
rth_df['cum_ret'] = (1 + rth_df['strategy_ret'].fillna(0)).cumprod()
rth_df['bh_ret'] = (1 + rth_df['pct_change'].fillna(0)).cumprod()

# Stats
total_ret = rth_df['cum_ret'].iloc[-1] - 1
bh_total_ret = rth_df['bh_ret'].iloc[-1] - 1
sharpe = np.sqrt(252 * 6.5 * 60) * rth_df['strategy_ret'].mean() / rth_df['strategy_ret'].std() # Annualized

# Drawdown
cum_max = rth_df['cum_ret'].cummax()
dd = (rth_df['cum_ret'] - cum_max) / cum_max
max_dd = dd.min()

print(f"Strategy Total Return: {total_ret:.2%}")
print(f"Buy & Hold Total Return: {bh_total_ret:.2%}")
print(f"Annualized Sharpe Ratio: {sharpe:.2f}")
print(f"Max Drawdown: {max_dd:.2%}")

# Plotting
plt.figure(figsize=(12, 6))
plt.plot(rth_df['cum_ret'], label='VWAP Holy Grail Strategy')
plt.plot(rth_df['bh_ret'], label='Buy & Hold (RTH Only)')
plt.title('VWAP Holy Grail Strategy Backtest on NQ')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid(True)
plt.savefig(rth_df.index[0].strftime('%Y%m%d') + '_backtest.png')

# Save stats to file
with open('vwap_backtest_results.txt', 'w') as f:
    f.write(f"Strategy: VWAP Holy Grail (Always In)\n")
    f.write(f"Period: {rth_df.index.min()} to {rth_df.index.max()}\n")
    f.write(f"Total Return: {total_ret:.2%}\n")
    f.write(f"Buy & Hold: {bh_total_ret:.2%}\n")
    f.write(f"Sharpe Ratio: {sharpe:.2f}\n")
    f.write(f"Max DD: {max_dd:.2%}\n")

print("Backtest complete. Results saved.")
