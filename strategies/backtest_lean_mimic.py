import pandas as pd
import numpy as np
from datetime import time, timedelta

# Load Data
print("Loading data for Lean-style backtest...")
df_raw = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df_raw = df_raw[~df_raw['symbol'].str.contains('-')].copy()
df_raw['ts_event'] = pd.to_datetime(df_raw['ts_event'])
df_raw = df_raw.set_index('ts_event').tz_convert('America/New_York')
df_raw['date'] = df_raw.index.date

# Active contract selection
daily_vol = df_raw.groupby([df_raw['date'], 'symbol'])['volume'].sum().reset_index()
active_symbols_map = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()].set_index('date')['symbol'].to_dict()

# Backtest Settings (Lean-like)
TICK_SIZE = 0.25
COMMISSION = 2.0  # $2 per side
SLIPPAGE_TICKS = 1
INITIAL_CASH = 100000
NQ_MULTIPLIER = 20

trades = []
cash = INITIAL_CASH

print("Starting Event-Driven Simulation...")

for date, day_data in df_raw.groupby('date'):
    active_sym = active_symbols_map.get(date)
    if not active_sym: continue
    
    # Filter for active symbol and RTH
    day_group = day_data[day_data['symbol'] == active_sym].sort_index()
    day_rth = day_group[(day_group.index.time >= time(9, 30)) & (day_group.index.time <= time(16, 0))]
    
    if day_rth.empty: continue
    
    # 1. ORB Calculation (09:30 - 10:00)
    orb_window = day_rth[(day_rth.index.time >= time(9, 30)) & (day_rth.index.time < time(10, 0))]
    if len(orb_window) < 30: continue
    
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # 2. Trading Session (After 10:00)
    trading_data = day_rth[day_rth.index.time >= time(10, 0)]
    
    state = "IDLE" # IDLE, PENDING_ENTRY, POSITION
    pos_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_time = None
    
    # Process bar by bar (Lean OnData style)
    bars = trading_data.to_dict('records')
    times = trading_data.index
    
    for i in range(len(bars)):
        bar = bars[i]
        curr_time = times[i]
        
        if state == "IDLE":
            # Signal Detection
            if curr_time.time() < time(15, 50):
                if bar['close'] > orb_h:
                    state = "PENDING_ENTRY"
                    pos_type = "Long"
                elif bar['close'] < orb_l:
                    state = "PENDING_ENTRY"
                    pos_type = "Short"
                    
        elif state == "PENDING_ENTRY":
            # Lean Entry: Next Bar Open + Slippage
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
            # Process the rest of the bar for exit
            
        if state == "POSITION":
            # Exit Detection (Check SL first, then TP, then EOD)
            exit_price = None
            reason = ""
            
            if pos_type == "Long":
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss - (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "SL"
                elif bar['high'] >= take_profit:
                    exit_price = take_profit - (SLIPPAGE_TICKS * TICK_SIZE) # Limit order slippage? usually fill at limit
                    reason = "TP"
                elif curr_time.time() >= time(15, 55):
                    exit_price = bar['close'] - (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "EOD"
            else: # Short
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss + (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "SL"
                elif bar['low'] <= take_profit:
                    exit_price = take_profit + (SLIPPAGE_TICKS * TICK_SIZE)
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
                    'entry_time': entry_time,
                    'exit_time': curr_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pts': pnl_pts,
                    'pnl_usd': pnl_usd,
                    'reason': reason
                })
                state = "FINISHED_DAY"
                break

# Results
trades_df = pd.DataFrame(trades)
if not trades_df.empty:
    trades_df['cum_pnl_usd'] = trades_df['pnl_usd'].cumsum()
    print("\n--- Lean-Mimic Backtest Results ---")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {(trades_df['pnl_pts'] > 0).mean()*100:.2f}%")
    print(f"Total USD PnL: ${trades_df['pnl_usd'].sum():,.2f}")
    print(f"Avg PnL per Trade: ${trades_df['pnl_usd'].mean():.2f}")
    
    trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_lean_mimic_trades.csv', index=False)
    
    # Plot
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 6))
    plt.plot(pd.to_datetime(trades_df['date']), trades_df['cum_pnl_usd'])
    plt.title('NQ 30m ORB Strategy Equity (Lean-Mimic USD)')
    plt.ylabel('USD PnL')
    plt.grid(True)
    plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_lean_equity.png')
else:
    print("No trades executed.")
