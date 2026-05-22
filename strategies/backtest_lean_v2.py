import pandas as pd
import numpy as np
from datetime import time

# Load Data
print("Loading data for Lean-style backtest V2...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df = df[~df['symbol'].str.contains('-')].copy()
df['ts_event'] = pd.to_datetime(df['ts_event'])
df = df.set_index('ts_event').tz_convert('America/New_York')
df['date_ny'] = df.index.date

# Active contract selection
daily_vol = df.groupby(['date_ny', 'symbol'])['volume'].sum().reset_index()
active_symbols_map = daily_vol.loc[daily_vol.groupby('date_ny')['volume'].idxmax()].set_index('date_ny')['symbol'].to_dict()

# Settings
TICK_SIZE = 0.25
COMMISSION = 2.01
SLIPPAGE_TICKS = 1
NQ_MULTIPLIER = 20

trades = []

print("Running Rigorous Event-Driven Backtest...")
for date, day_group in df.groupby('date_ny'):
    active_sym = active_symbols_map.get(date)
    day_data = day_group[day_group['symbol'] == active_sym].sort_index()
    
    # RTH filter
    day_rth = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time <= time(16, 0))]
    if day_rth.empty: continue
    
    # ORB (09:30 - 10:00)
    orb_window = day_rth[(day_rth.index.time >= time(9, 30)) & (day_rth.index.time < time(10, 0))]
    if orb_window.empty: continue
    
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # Trading (From 10:00)
    trading_data = day_rth[day_rth.index.time >= time(10, 0)]
    
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
            # Allow bar to hit SL/TP immediately if needed
            
        if state == "POSITION":
            exit_price = None
            reason = ""
            
            if pos_type == "Long":
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss - (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "SL"
                elif bar['high'] >= take_profit:
                    exit_price = take_profit # Limit fill
                    reason = "TP"
                elif curr_time.time() >= time(15, 55):
                    exit_price = bar['close'] - (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "EOD"
            else:
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss + (SLIPPAGE_TICKS * TICK_SIZE)
                    reason = "SL"
                elif bar['low'] <= take_profit:
                    exit_price = take_profit # Limit fill
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
                    'pnl_usd': pnl_usd,
                    'reason': reason
                })
                state = "FINISHED"
                break

trades_df = pd.DataFrame(trades)
if not trades_df.empty:
    print(f"\n--- Lean-style Backtest Results (V2) ---")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {(trades_df['pnl_usd'] > 0).mean()*100:.2f}%")
    print(f"Total PnL: ${trades_df['pnl_usd'].sum():,.2f}")
    
    trades_df['cum_pnl'] = trades_df['pnl_usd'].cumsum()
    
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 6))
    plt.plot(trades_df['date'], trades_df['cum_pnl'])
    plt.title('NQ ORB 30m Lean-style Equity Curve (USD)')
    plt.grid(True)
    plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_lean_v2.png')
    trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_lean_v2_trades.csv', index=False)
else:
    print("No trades found.")
