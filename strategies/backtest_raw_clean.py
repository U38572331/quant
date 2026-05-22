import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
print("Loading DataBento data for RAW strategy re-run...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')

# Settings (RAW Strategy)
NQ_MULTIPLIER = 20
COMMISSION = 0 # Temporarily set to 0 to see raw performance
SLIPPAGE = 0    # Temporarily set to 0

trades = []

print("Running Raw 30m ORB Backtest (Long/Short, 1:1 RR)...")
for date, day_data in df.groupby('date'):
    day_data = day_data.sort_index()
    
    # ORB (09:30 - 10:00)
    orb_window = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time < time(10, 0))]
    if orb_window.empty: continue
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # Trading (From 10:00)
    trading_data = day_data[day_data.index.time >= time(10, 0)]
    bars = trading_data.to_dict('records')
    times = trading_data.index
    
    state = "IDLE"
    pos_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    
    for i in range(len(bars)):
        bar = bars[i]
        curr_time = times[i]
        
        if state == "IDLE":
            if curr_time.time() < time(15, 50):
                if bar['close'] > orb_h:
                    state = "PENDING_ENTRY"
                    pos_type = "Long"
                elif bar['close'] < orb_l:
                    state = "PENDING_ENTRY"
                    pos_type = "Short"
                    
        elif state == "PENDING_ENTRY":
            # Entry at Signal Bar Close (Assuming 1:1 with TV logic)
            # Actually TV enters at next bar open, but let's try close first to see if it matches user expectation
            fill = bar['open'] 
            entry_price = fill
            if pos_type == "Long":
                stop_loss = orb_l
                take_profit = fill + (fill - stop_loss)
            else:
                stop_loss = orb_h
                take_profit = fill - (stop_loss - fill)
            state = "POSITION"
            
        if state == "POSITION":
            exit_price = None
            
            if pos_type == "Long":
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                elif curr_time.time() >= time(15, 55):
                    exit_price = bar['close']
            else:
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                elif bar['low'] <= take_profit:
                    exit_price = take_profit
                elif curr_time.time() >= time(15, 55):
                    exit_price = bar['close']
            
            if exit_price is not None:
                pnl_pts = (exit_price - entry_price) if pos_type == "Long" else (entry_price - exit_price)
                trades.append({
                    'date': date,
                    'type': pos_type,
                    'pnl_pts': pnl_pts,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'orb_h': orb_h,
                    'orb_l': orb_l
                })
                state = "FINISHED"
                break

trades_df = pd.DataFrame(trades)
print(f"\n--- Raw Strategy Results (No Slippage/Commissions) ---")
print(f"Total Trades: {len(trades_df)}")
print(f"Win Rate: {(trades_df['pnl_pts'] > 0).mean()*100:.2f}%")
print(f"Total Points: {trades_df['pnl_pts'].sum():,.2f}")

# Sample trade for verification
print("\n--- Sample Trade for Verification (Latest) ---")
print(trades_df.tail(1).to_string())

trades_df['cum_pts'] = trades_df['pnl_pts'].cumsum()
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.plot(pd.to_datetime(trades_df['date']), trades_df['cum_pts'])
plt.title('NQ 30m ORB Raw Points (Clean Data, No Friction)')
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_points.png')
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_trades.csv', index=False)
