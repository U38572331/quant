import pandas as pd
import numpy as np
from datetime import time

# Load Clean Data
print("Loading DataBento data for optimization...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')
df['date'] = pd.to_datetime(df.index.date)

# Calculate Daily EMA 200 for Trend Filter
print("Calculating Trend Filter (Daily EMA 200)...")
daily_close = df.groupby('date')['close'].last().to_frame()
daily_close['ema200'] = daily_close['close'].ewm(span=200, adjust=False).mean()
df = df.merge(daily_close[['ema200']], left_on='date', right_index=True, how='left')

# Settings
TICK_SIZE = 0.25
COMMISSION = 2.01
SLIPPAGE_TICKS = 1
NQ_MULTIPLIER = 20
RR_RATIO = 1.5 # Optimized RR

trades = []

print(f"Running Optimized Backtest (Long Only + EMA200 + {RR_RATIO} RR)...")
for date, day_data in df.groupby('date'):
    day_data = day_data.sort_index()
    
    # Trend Filter: Price must be above EMA 200
    if day_data['ema200'].iloc[0] is None or day_data['close'].iloc[0] < day_data['ema200'].iloc[0]:
        continue
    
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
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    
    for i in range(len(bars)):
        bar = bars[i]
        curr_time = times[i]
        
        if state == "IDLE":
            if curr_time.time() < time(15, 50):
                if bar['close'] > orb_h: # Long Only
                    state = "PENDING_ENTRY"
                    
        elif state == "PENDING_ENTRY":
            fill = bar['open'] + SLIPPAGE_TICKS * TICK_SIZE
            entry_price = fill
            stop_loss = orb_l
            take_profit = fill + (fill - stop_loss) * RR_RATIO
            state = "POSITION"
            
        if state == "POSITION":
            exit_price = None
            reason = ""
            
            if bar['low'] <= stop_loss:
                exit_price = stop_loss - (SLIPPAGE_TICKS * TICK_SIZE)
                reason = "SL"
            elif bar['high'] >= take_profit:
                exit_price = take_profit
                reason = "TP"
            elif curr_time.time() >= time(15, 55):
                exit_price = bar['close'] - (SLIPPAGE_TICKS * TICK_SIZE)
                reason = "EOD"
            
            if exit_price is not None:
                pnl_pts = exit_price - entry_price
                pnl_usd = (pnl_pts * NQ_MULTIPLIER) - (COMMISSION * 2)
                
                trades.append({
                    'date': date,
                    'pnl_usd': pnl_usd,
                    'reason': reason
                })
                state = "FINISHED"
                break

trades_df = pd.DataFrame(trades)
if not trades_df.empty:
    print(f"\n--- Optimized Results ---")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {(trades_df['pnl_usd'] > 0).mean()*100:.2f}%")
    print(f"Total PnL: ${trades_df['pnl_usd'].sum():,.2f}")
    
    trades_df['cum_pnl'] = trades_df['pnl_usd'].cumsum()
    
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 6))
    plt.plot(pd.to_datetime(trades_df['date']), trades_df['cum_pnl'], color='orange')
    plt.title(f'NQ Optimized ORB Strategy (Long Only + EMA200 + {RR_RATIO} RR)')
    plt.ylabel('USD PnL')
    plt.grid(True)
    trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_optimized_trades.csv', index=False)
    print("Optimized trades saved to nq_optimized_trades.csv")
else:
    print("No trades found with these filters.")
