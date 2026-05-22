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
df.index = df.index.tz_convert('US/Eastern')

# Clean data
core_cols = ['open', 'high', 'low', 'close', 'volume']
df = df.dropna(subset=core_cols)
df = df[df['volume'] > 0]

# Filter for RTH (9:30 AM to 4:00 PM)
rth_df = df.between_time('09:30', '16:00').copy()

if rth_df.empty:
    print("Error: RTH data is empty!")
    exit()

# Optimized VWAP Calculation (Vectorized)
print("Calculating Daily VWAP...")
rth_df['date'] = rth_df.index.date
rth_df['tp'] = (rth_df['high'] + rth_df['low'] + rth_df['close']) / 3
rth_df['pv'] = rth_df['tp'] * rth_df['volume']

# Grouped cumulative sum
rth_df['cum_pv'] = rth_df.groupby('date')['pv'].cumsum()
rth_df['cum_vol'] = rth_df.groupby('date')['volume'].cumsum()
rth_df['my_vwap'] = rth_df['cum_pv'] / rth_df['cum_vol']

# Define Strategy: Always-in-the-market
rth_df['signal'] = np.where(rth_df['close'] > rth_df['my_vwap'], 1, -1)
rth_df['position'] = rth_df['signal'].shift(1)

# Calculate Returns
rth_df['pct_change'] = rth_df['close'].pct_change()
# On the first minute of each day, shift position might be from previous day or NaN. 
# We should avoid carrying positions over the night if it's an intraday strategy.
# The paper says it exits at end of day.
# To simulate this, we'll zero out the first minute's return or use log returns within the day.
rth_df.loc[rth_df.groupby('date').head(1).index, 'pct_change'] = 0

rth_df['strategy_ret'] = rth_df['position'] * rth_df['pct_change']

# Remove any remaining NaNs in returns
rth_df['strategy_ret'] = rth_df['strategy_ret'].fillna(0)
rth_df['pct_change'] = rth_df['pct_change'].fillna(0)

# Cumulative Returns
rth_df['cum_ret'] = (1 + rth_df['strategy_ret']).cumprod()
rth_df['bh_ret'] = (1 + rth_df['pct_change']).cumprod()

# Stats
total_ret = rth_df['cum_ret'].iloc[-1] - 1
bh_total_ret = rth_df['bh_ret'].iloc[-1] - 1
# Sharpe (daily approximation)
daily_rets = rth_df.groupby('date')['strategy_ret'].sum()
sharpe = np.sqrt(252) * daily_rets.mean() / daily_rets.std()

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
plt.yscale('log') # Use log scale because return might be huge over 14 years
plt.title('VWAP Holy Grail Strategy Backtest on NQ (Log Scale)')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid(True)
plt.savefig('vwap_backtest_fixed.png')

# Save stats to file
with open('vwap_backtest_results_fixed.txt', 'w') as f:
    f.write(f"Strategy: VWAP Holy Grail (Always In)\n")
    f.write(f"Period: {rth_df.index.min()} to {rth_df.index.max()}\n")
    f.write(f"Total Return: {total_ret:.2%}\n")
    f.write(f"Buy & Hold: {bh_total_ret:.2%}\n")
    f.write(f"Sharpe Ratio: {sharpe:.2f}\n")
    f.write(f"Max DD: {max_dd:.2%}\n")

print("Backtest complete. Results saved.")
