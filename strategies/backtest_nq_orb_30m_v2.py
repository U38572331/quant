import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import time

# Load Data
print("Loading data...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')

# Filter for clean symbols (non-spreads)
df = df[~df['symbol'].str.contains('-')].copy()

# Convert to NY time
print("Processing timezones...")
df['ts_event'] = pd.to_datetime(df['ts_event'])
df = df.set_index('ts_event').tz_convert('America/New_York')
df['date'] = df.index.date
df['time'] = df.index.time

# Select the most active symbol per day based on total volume
print("Selecting active contracts...")
daily_volume = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
active_symbols = daily_volume.loc[daily_volume.groupby('date')['volume'].idxmax()]
active_symbols_map = active_symbols.set_index('date')['symbol'].to_dict()

# Filter df to only include the active symbol for each day
def filter_active(group):
    date = group.name
    active_sym = active_symbols_map.get(date)
    return group[group['symbol'] == active_sym]

# This might be slow, let's try a merge instead
df['is_active'] = df.apply(lambda x: x['symbol'] == active_symbols_map.get(x['date']), axis=1)
df_active = df[df['is_active']].copy()

# Filter for RTH (09:30 - 16:00)
df_rth = df_active[(df_active.index.time >= time(9, 30)) & (df_active.index.time <= time(16, 0))].copy()

# Identify ORB (09:30 - 10:00)
print("Calculating ORB levels...")
orb_window = df_rth[(df_rth.index.time >= time(9, 30)) & (df_rth.index.time < time(10, 0))]
orb_levels = orb_window.groupby('date').agg({'high': 'max', 'low': 'min'}).rename(columns={'high': 'orb_high', 'low': 'orb_low'})

# Merge ORB levels back
df_rth = df_rth.merge(orb_levels, left_on='date', right_index=True, how='left')

# Backtest Variables
rr = 1.0
trades = []

print("Running backtest...")
for date, group in df_rth.groupby('date'):
    if group['orb_high'].isna().any():
        continue
    
    orb_h = group['orb_high'].iloc[0]
    orb_l = group['orb_low'].iloc[0]
    
    # Only trade after 10:00
    after_orb = group[group.index.time >= time(10, 0)]
    
    pos = 0  # 1 for long, -1 for short
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_time = None
    
    for idx, row in after_orb.iterrows():
        curr_time = row.name.time()
        curr_close = row['close']
        curr_high = row['high']
        curr_low = row['low']
        
        if pos == 0:
            if curr_time < time(15, 55):
                if curr_close > orb_h:
                    pos = 1
                    entry_price = curr_close
                    stop_loss = orb_l
                    risk = entry_price - stop_loss
                    if risk <= 5: # Minimal risk filter to avoid noise/bad data
                        pos = 0
                        continue
                    take_profit = entry_price + (risk * rr)
                    entry_time = row.name
                elif curr_close < orb_l:
                    pos = -1
                    entry_price = curr_close
                    stop_loss = orb_h
                    risk = stop_loss - entry_price
                    if risk <= 5:
                        pos = 0
                        continue
                    take_profit = entry_price - (risk * rr)
                    entry_time = row.name
        else:
            exit_price = None
            exit_reason = ""
            
            if pos == 1:
                if curr_low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                elif curr_high >= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"
                elif curr_time >= time(15, 55):
                    exit_price = curr_close
                    exit_reason = "EOD"
            elif pos == -1:
                if curr_high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                elif curr_low <= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"
                elif curr_time >= time(15, 55):
                    exit_price = curr_close
                    exit_reason = "EOD"
            
            if exit_price is not None:
                pnl = (exit_price - entry_price) * pos
                trades.append({
                    'date': date,
                    'entry_time': entry_time,
                    'exit_time': row.name,
                    'symbol': row['symbol'],
                    'type': 'Long' if pos == 1 else 'Short',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'reason': exit_reason
                })
                break

# Results Analysis
trades_df = pd.DataFrame(trades)
if trades_df.empty:
    print("No trades found.")
else:
    trades_df['cum_pnl'] = trades_df['pnl'].cumsum()
    win_rate = (trades_df['pnl'] > 0).mean() * 100
    total_pnl = trades_df['pnl'].sum()
    
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    profit_factor = wins / losses if losses != 0 else np.inf
    
    print(f"\n--- Backtest Results (30m ORB, RR {rr}) ---")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL (points): {total_pnl:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    plt.figure(figsize=(12, 6))
    plt.plot(trades_df['exit_time'], trades_df['cum_pnl'], label='Cumulative PnL (Points)')
    plt.title(f'NQ 30m ORB Strategy Equity Curve (RR {rr})')
    plt.xlabel('Date')
    plt.ylabel('PnL Points')
    plt.grid(True)
    plt.legend()
    plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_equity_30m_fixed.png')
    trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_30m_fixed.csv', index=False)
    print("\nResults saved.")
