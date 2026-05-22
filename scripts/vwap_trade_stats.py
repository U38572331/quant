import pandas as pd
import numpy as np
import os

# Load data (using the same logic as v5)
file_path = r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet'
df = pd.read_parquet(file_path)

df['ts_event'] = pd.to_datetime(df['ts_event'])
df.set_index('ts_event', inplace=True)
df.sort_index(inplace=True)
df.index = df.index.tz_convert('US/Eastern')

# Front contract selection
df['date'] = df.index.date
daily_vol = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_symbols = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()]
symbol_map = front_symbols.set_index('date')['symbol'].to_dict()
df['front_symbol'] = df['date'].map(symbol_map)
df_front = df[df['symbol'] == df['front_symbol']].copy()

rth_df = df_front.between_time('09:30', '16:00').copy()
rth_df.sort_index(inplace=True)

# VWAP
rth_df['tp'] = (rth_df['high'] + rth_df['low'] + rth_df['close']) / 3
rth_df['pv'] = rth_df['tp'] * rth_df['volume']
rth_df['cum_pv'] = rth_df.groupby('date')['pv'].transform('cumsum')
rth_df['cum_vol'] = rth_df.groupby('date')['volume'].transform('cumsum')
rth_df['my_vwap'] = rth_df['cum_pv'] / rth_df['cum_vol']

# Signal and Position
rth_df['signal'] = np.where(rth_df['close'] > rth_df['my_vwap'], 1, -1)
rth_df['position'] = rth_df['signal'].shift(1)
rth_df['symbol_changed'] = rth_df['symbol'] != rth_df['symbol'].shift(1)
rth_df.loc[rth_df['symbol_changed'], 'position'] = 0

# Extract Trades
# A trade starts when signal changes or day starts, and ends when signal flips or day ends
# We can identify trade groups by checking for changes in position
rth_df['trade_id'] = (rth_df['position'] != rth_df['position'].shift(1)).cumsum()

# Calculate return per minute
rth_df['log_ret'] = np.log(rth_df['close'] / rth_df['close'].shift(1))
rth_df.loc[rth_df['symbol_changed'], 'log_ret'] = 0
rth_df.loc[rth_df.groupby('date').head(1).index, 'log_ret'] = 0
rth_df['strategy_log_ret'] = rth_df['position'] * rth_df['log_ret']

# Aggregate by trade_id
trade_stats = rth_df.groupby('trade_id').agg({
    'strategy_log_ret': 'sum',
    'position': 'first',
    'symbol': 'first',
    'date': 'first'
})

# Filter out rows where position was 0 (no trade)
trade_stats = trade_stats[trade_stats['position'] != 0].copy()

# Convert log returns to percentage for readability
trade_stats['ret_pct'] = (np.exp(trade_stats['strategy_log_ret']) - 1) * 100

# Win Rate Stats
wins = trade_stats[trade_stats['ret_pct'] > 0]
losses = trade_stats[trade_stats['ret_pct'] <= 0]

total_trades = len(trade_stats)
win_rate = len(wins) / total_trades * 100
avg_win = wins['ret_pct'].mean()
avg_loss = losses['ret_pct'].mean()
profit_factor = wins['ret_pct'].sum() / abs(losses['ret_pct'].sum())

print(f"Total Trades: {total_trades}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Average Win: {avg_win:.4f}%")
print(f"Average Loss: {avg_loss:.4f}%")
print(f"Profit Factor: {profit_factor:.2f}")

# Long vs Short
long_trades = trade_stats[trade_stats['position'] == 1]
short_trades = trade_stats[trade_stats['position'] == -1]

print(f"\nLong Win Rate: {(len(long_trades[long_trades['ret_pct'] > 0]) / len(long_trades) * 100):.2f}%")
print(f"Short Win Rate: {(len(short_trades[short_trades['ret_pct'] > 0]) / len(short_trades) * 100):.2f}%")

# Max Drawdown of the trades
trade_stats['cum_ret'] = (1 + trade_stats['ret_pct']/100).cumprod()
cum_max = trade_stats['cum_ret'].cummax()
dd = (trade_stats['cum_ret'] - cum_max) / cum_max
max_dd = dd.min() * 100

with open('vwap_trade_stats.txt', 'w') as f:
    f.write(f"Total Trades: {total_trades}\n")
    f.write(f"Win Rate: {win_rate:.2f}%\n")
    f.write(f"Average Win: {avg_win:.4f}%\n")
    f.write(f"Average Loss: {avg_loss:.4f}%\n")
    f.write(f"Profit Factor: {profit_factor:.2f}\n")
    f.write(f"Max DD: {max_dd:.2f}%\n")

print("Trade stats calculation complete.")
