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

# 1. Select the Front Contract (Max volume per day)
print("Selecting front contracts...")
df['date'] = df.index.date
daily_vol = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
# Find symbol with max volume per day
front_symbols = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()]
# Create a mapping of date -> front symbol
symbol_map = front_symbols.set_index('date')['symbol'].to_dict()

# Map the front symbol back to the main dataframe
df['front_symbol'] = df['date'].map(symbol_map)
# Filter for only the front contract rows
df_front = df[df['symbol'] == df['front_symbol']].copy()

# Filter for RTH
rth_df = df_front.between_time('09:30', '16:00').copy()
rth_df.sort_index(inplace=True)

# 2. Optimized VWAP Calculation
print("Calculating Daily VWAP...")
rth_df['tp'] = (rth_df['high'] + rth_df['low'] + rth_df['close']) / 3
rth_df['pv'] = rth_df['tp'] * rth_df['volume']

rth_df['cum_pv'] = rth_df.groupby('date')['pv'].transform('cumsum')
rth_df['cum_vol'] = rth_df.groupby('date')['volume'].transform('cumsum')
rth_df['my_vwap'] = rth_df['cum_pv'] / rth_df['cum_vol']

# 3. Define Strategy
rth_df['signal'] = np.where(rth_df['close'] > rth_df['my_vwap'], 1, -1)
rth_df['position'] = rth_df['signal'].shift(1)

# Handle Rollovers (where symbol changes from yesterday to today)
rth_df['symbol_changed'] = rth_df['symbol'] != rth_df['symbol'].shift(1)
rth_df.loc[rth_df['symbol_changed'], 'position'] = 0

# 4. Returns
rth_df['log_ret'] = np.log(rth_df['close'] / rth_df['close'].shift(1))
rth_df.loc[rth_df['symbol_changed'], 'log_ret'] = 0
rth_df.loc[rth_df.groupby('date').head(1).index, 'log_ret'] = 0

rth_df['strategy_log_ret'] = rth_df['position'] * rth_df['log_ret']
rth_df['strategy_log_ret'] = rth_df['strategy_log_ret'].fillna(0)

# Cumulative Equity
rth_df['cum_log_ret'] = rth_df['strategy_log_ret'].cumsum()
rth_df['bh_log_ret'] = rth_df['log_ret'].fillna(0).cumsum()

# 5. Final Stats
total_ret_pct = (np.exp(rth_df['cum_log_ret'].iloc[-1]) - 1) * 100
bh_ret_pct = (np.exp(rth_df['bh_log_ret'].iloc[-1]) - 1) * 100

# Annualized Sharpe
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
plt.plot(np.exp(rth_df['bh_log_ret']), label='Buy & Hold (RTH)')
plt.title('VWAP Holy Grail Strategy on NQ (Continuous Front Contract)')
plt.legend()
plt.grid(True)
plt.savefig('vwap_backtest_continuous.png')

print("Backtest complete.")
