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

# Filter for main NQ symbols only (length 4, e.g. NQM2)
# Calendar spreads (NQM2-NQZ2) cause huge price jumps and must be removed
df = df[df['symbol'].str.len() == 4].copy()
print(f"Remaining symbols after filtering: {df['symbol'].unique()[:10]}...")

# Clean data
df = df[df['close'] > 100] # NQ should be well above 100
df = df[df['volume'] > 0]

# Filter for RTH
rth_df = df.between_time('09:30', '16:00').copy()

# Sort by symbol and time to handle rollovers
rth_df = rth_df.sort_values(['symbol', 'ts_event'])

# Optimized VWAP Calculation
print("Calculating Daily VWAP...")
rth_df['date'] = rth_df.index.date
rth_df['tp'] = (rth_df['high'] + rth_df['low'] + rth_df['close']) / 3
rth_df['pv'] = rth_df['tp'] * rth_df['volume']

# Daily anchored VWAP
rth_df['cum_pv'] = rth_df.groupby(['date', 'symbol'])['pv'].transform('cumsum')
rth_df['cum_vol'] = rth_df.groupby(['date', 'symbol'])['volume'].transform('cumsum')
rth_df['my_vwap'] = rth_df['cum_pv'] / rth_df['cum_vol']

# Define Strategy: Always-in-the-market
rth_df['signal'] = np.where(rth_df['close'] > rth_df['my_vwap'], 1, -1)
rth_df['position'] = rth_df['signal'].shift(1)

# Handle Symbol Change (avoid jump when shifting from one contract to another)
rth_df['symbol_changed'] = rth_df['symbol'] != rth_df['symbol'].shift(1)
rth_df.loc[rth_df['symbol_changed'], 'position'] = 0

# Log Returns
rth_df['log_ret'] = np.log(rth_df['close'] / rth_df['close'].shift(1))
# Zero out at symbol change and at start of each day
rth_df.loc[rth_df['symbol_changed'], 'log_ret'] = 0
rth_df.loc[rth_df.groupby('date').head(1).index, 'log_ret'] = 0

rth_df['strategy_log_ret'] = rth_df['position'] * rth_df['log_ret']
rth_df['strategy_log_ret'] = rth_df['strategy_log_ret'].fillna(0)

# Cumulative Equity
rth_df['cum_log_ret'] = rth_df['strategy_log_ret'].cumsum()
rth_df['bh_log_ret'] = rth_df['log_ret'].fillna(0).cumsum()

# Final Stats
total_ret_pct = (np.exp(rth_df['cum_log_ret'].iloc[-1]) - 1) * 100
bh_ret_pct = (np.exp(rth_df['bh_log_ret'].iloc[-1]) - 1) * 100

# Annualized Sharpe (from daily log rets)
daily_log_rets = rth_df.groupby('date')['strategy_log_ret'].sum()
sharpe = np.sqrt(252) * daily_log_rets.mean() / daily_log_rets.std()

# Drawdown
cum_max_log = rth_df['cum_log_ret'].cummax()
log_dd = rth_df['cum_log_ret'] - cum_max_log
max_dd_pct = (np.exp(log_dd.min()) - 1) * 100

print(f"Strategy Total Return: {total_ret_pct:.2f}%")
print(f"Buy & Hold Total Return: {bh_ret_pct:.2f}%")
print(f"Annualized Sharpe Ratio: {sharpe:.2f}")
print(f"Max Drawdown: {max_dd_pct:.2f}%")

# Plotting
plt.figure(figsize=(12, 6))
plt.plot(np.exp(rth_df['cum_log_ret']), label='VWAP Holy Grail Strategy')
plt.plot(np.exp(rth_df['bh_log_ret']), label='Buy & Hold (RTH Only)')
plt.yscale('log')
plt.title('VWAP Holy Grail Strategy on NQ (Log Equity)')
plt.legend()
plt.grid(True)
plt.savefig('vwap_backtest_final.png')

# Save a CSV for verification
rth_df[['close', 'my_vwap', 'position', 'strategy_log_ret']].tail(1000).to_csv('vwap_check.csv')

print("Backtest complete.")
