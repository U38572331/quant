import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import time

# Load Data
print("Loading data...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df = df[~df['symbol'].str.contains('-')].copy()

# Convert to NY time
df['ts_event'] = pd.to_datetime(df['ts_event'])
df = df.set_index('ts_event').tz_convert('America/New_York')
df['date'] = df.index.date

# Active contract selection (improved)
daily_volume = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
active_symbols = daily_volume.loc[daily_volume.groupby('date')['volume'].idxmax()]
active_symbols_map = active_symbols.set_index('date')['symbol'].to_dict()

df['is_active'] = df['symbol'] == df['date'].map(active_symbols_map)
df_active = df[df['is_active']].copy()

# Filter for RTH
df_rth = df_active[(df_active.index.time >= time(9, 30)) & (df_active.index.time <= time(16, 0))].copy()

# ORB
orb_window = df_rth[(df_rth.index.time >= time(9, 30)) & (df_rth.index.time < time(10, 0))]
orb_levels = orb_window.groupby('date').agg({'high': 'max', 'low': 'min'}).rename(columns={'high': 'orb_high', 'low': 'orb_low'})
df_rth = df_rth.merge(orb_levels, left_on='date', right_index=True, how='left')

# Backtest with Percentage Returns
# Assumption: Risk 1% of capital per trade. SL is the opposite side of ORB.
trades = []
rr = 1.0

print("Running normalized backtest...")
for date, group in df_rth.groupby('date'):
    if group['orb_high'].isna().any(): continue
    
    orb_h = group['orb_high'].iloc[0]
    orb_l = group['orb_low'].iloc[0]
    orb_width = orb_h - orb_l
    
    # Filter out extreme ORB widths (possible bad data or abnormal volatility)
    # Average NQ ORB 30m width is usually 50-200 points. If > 500 or < 5, it's suspicious.
    if orb_width < 5 or orb_width > 600: continue
    
    after_orb = group[group.index.time >= time(10, 0)]
    pos = 0
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
            if curr_time < time(15, 50):
                if curr_close > orb_h:
                    pos = 1
                    entry_price = curr_close
                    stop_loss = orb_l
                    take_profit = entry_price + (entry_price - stop_loss) * rr
                    entry_time = row.name
                elif curr_close < orb_l:
                    pos = -1
                    entry_price = curr_close
                    stop_loss = orb_h
                    take_profit = entry_price - (stop_loss - entry_price) * rr
                    entry_time = row.name
        else:
            exit_price = None
            if pos == 1:
                if curr_low <= stop_loss: exit_price = stop_loss
                elif curr_high >= take_profit: exit_price = take_profit
                elif curr_time >= time(15, 55): exit_price = curr_close
            elif pos == -1:
                if curr_high >= stop_loss: exit_price = stop_loss
                elif curr_low <= take_profit: exit_price = take_profit
                elif curr_time >= time(15, 55): exit_price = curr_close
            
            if exit_price is not None:
                # Calculate R (Reward/Risk unit)
                # Risk = Entry - SL (for Long)
                risk_pts = abs(entry_price - stop_loss)
                pnl_pts = (exit_price - entry_price) * pos
                pnl_r = pnl_pts / risk_pts
                
                # Check for outliers (more than 2R is impossible with this logic unless gap)
                if abs(pnl_r) > 2.5: continue 
                
                trades.append({
                    'date': date,
                    'type': 'Long' if pos == 1 else 'Short',
                    'pnl_pts': pnl_pts,
                    'pnl_r': pnl_r,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'symbol': row['symbol']
                })
                break

trades_df = pd.DataFrame(trades)
trades_df['cum_r'] = trades_df['pnl_r'].cumsum()

print(f"\n--- Normalized Results (Risk Units) ---")
print(f"Total Trades: {len(trades_df)}")
print(f"Total R gained: {trades_df['pnl_r'].sum():.2f}")
print(f"Win Rate: {(trades_df['pnl_r'] > 0).mean()*100:.2f}%")

plt.figure(figsize=(12, 6))
plt.plot(trades_df['date'], trades_df['cum_r'])
plt.title('NQ 30m ORB Strategy Equity (Cumulative R)')
plt.ylabel('R Units')
plt.grid(True)
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_equity_r.png')
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_r.csv', index=False)
