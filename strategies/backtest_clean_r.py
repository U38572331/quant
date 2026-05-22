import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
print("Loading Clean DataBento data for Normalized R-unit run...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')

trades = []

print("Running R-unit Backtest (Long/Short, 1:1 RR)...")
for date, day_data in df.groupby('date'):
    day_data = day_data.sort_index()
    
    # ORB (09:30 - 10:00)
    orb_window = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time < time(10, 0))]
    if orb_window.empty: continue
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # Trading logic
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
            fill = bar['open'] 
            entry_price = fill
            if pos_type == "Long":
                stop_loss = orb_l
                take_profit = fill + (fill - stop_loss)
                risk_pts = fill - stop_loss
            else:
                stop_loss = orb_h
                take_profit = fill - (stop_loss - fill)
                risk_pts = stop_loss - fill
            
            if risk_pts < 1: risk_pts = 1 # Avoid div by zero
            state = "POSITION"
            
        if state == "POSITION":
            exit_price = None
            
            if pos_type == "Long":
                if bar['low'] <= stop_loss: exit_price = stop_loss
                elif bar['high'] >= take_profit: exit_price = take_profit
                elif curr_time.time() >= time(15, 55): exit_price = bar['close']
            else:
                if bar['high'] >= stop_loss: exit_price = stop_loss
                elif bar['low'] <= take_profit: exit_price = take_profit
                elif curr_time.time() >= time(15, 55): exit_price = bar['close']
            
            if exit_price is not None:
                pnl_pts = (exit_price - entry_price) if pos_type == "Long" else (entry_price - exit_price)
                pnl_r = pnl_pts / risk_pts
                
                trades.append({
                    'date': date,
                    'type': pos_type,
                    'pnl_r': pnl_r,
                    'pnl_pts': pnl_pts
                })
                state = "FINISHED"
                break

trades_df = pd.DataFrame(trades)
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_clean_trades_r.csv', index=False)
print("R-unit results saved.")
