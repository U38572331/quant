import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
print("Loading Clean DataBento RTH data...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')

# Settings
TICK_SIZE = 0.25
COMMISSION = 2.01
SLIPPAGE_TICKS = 1
NQ_MULTIPLIER = 20

trades = []

print("Running Final Lean-style Backtest on Clean Data...")
for date, day_data in df.groupby('date'):
    day_data = day_data.sort_index()
    
    # ORB (09:30 - 10:00)
    orb_window = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time < time(10, 0))]
    if orb_window.empty: continue
    
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # Trading (From 10:00)
    trading_data = day_data[day_data.index.time >= time(10, 0)]
    
    state = "IDLE"
    pos_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_time = None
    
    bars = trading_data.to_dict('records')
    times = trading_data.index
    
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
            # Fill at next bar open
            fill_price = bar['open']
            if pos_type == "Long":
                fill_price += SLIPPAGE_TICKS * TICK_SIZE
                stop_loss = orb_l
                take_profit = fill_price + (fill_price - stop_loss)
            else:
                fill_price -= SLIPPAGE_TICKS * TICK_SIZE
                stop_loss = orb_h
                take_profit = fill_price - (stop_loss - fill_price)
            
            entry_price = fill_price
            entry_time = curr_time
            state = "POSITION"
            
        if state == "POSITION":
            exit_price = None
            reason = ""
            
            if pos_type == "Long":
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss - (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "SL"
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                    reason = "TP"
                elif curr_time.time() >= time(15, 55):
                    exit_price = bar['close'] - (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "EOD"
            else:
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss + (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "SL"
                elif bar['low'] <= take_profit:
                    exit_price = take_profit
                    reason = "TP"
                elif curr_time.time() >= time(15, 55):
                    exit_price = bar['close'] + (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "EOD"
            
            if exit_price is not None:
                pnl_pts = (exit_price - entry_price) if pos_type == "Long" else (entry_price - exit_price)
                pnl_usd = (pnl_pts * NQ_MULTIPLIER) - (COMMISSION * 2)
                
                trades.append({
                    'date': date,
                    'type': pos_type,
                    'pnl_usd': pnl_usd,
                    'pnl_pts': pnl_pts,
                    'reason': reason
                })
                state = "FINISHED"
                break

trades_df = pd.DataFrame(trades)
if not trades_df.empty:
    print(f"\n--- Final Lean-style Results (Clean Data) ---")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {(trades_df['pnl_usd'] > 0).mean()*100:.2f}%")
    print(f"Total PnL: ${trades_df['pnl_usd'].sum():,.2f}")
    
    trades_df['cum_pnl'] = trades_df['pnl_usd'].cumsum()
    
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 6))
    plt.plot(pd.to_datetime(trades_df['date']), trades_df['cum_pnl'])
    plt.title('NQ ORB 30m Final Lean-style Equity Curve (USD) - Clean Data')
    plt.ylabel('USD PnL')
    plt.grid(True)
    plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_lean_equity.png')
    trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_final_lean_trades.csv', index=False)
else:
    print("No trades found.")
