import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import time

# 1. Load Data
dbn_path = r'C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn'
print("Step 1: Loading DataBento DBN...")
store = db.DBNStore.from_file(dbn_path)
df = store.to_df()

# 2. Filtering & Timezone
print("Step 2: Processing Timezones and Symbols...")
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-')].copy()
df.index = pd.to_datetime(df.index)
df = df.tz_convert('America/New_York')
df['date_ny'] = df.index.date

# 3. Active Contract Selection
print("Step 3: Selecting Active Contracts...")
daily_vol = df.groupby(['date_ny', 'symbol'])['volume'].sum().reset_index()
active_map = daily_vol.loc[daily_vol.groupby('date_ny')['volume'].idxmax()].set_index('date_ny')['symbol'].to_dict()

# 4. Rigorous Backtest Loop
TICK_SIZE = 0.25
COMMISSION = 2.01
SLIPPAGE_TICKS = 1
NQ_MULTIPLIER = 20
INITIAL_CASH = 100000

trades = []

print("Step 4: Running Master Event-Driven Backtest...")
for date, day_group in df.groupby('date_ny'):
    active_sym = active_map.get(date)
    day_data = day_group[day_group['symbol'] == active_sym].sort_index()
    
    # RTH only (09:30 - 16:00)
    day_rth = day_data[(day_data.index.time >= time(9, 30)) & (day_data.index.time <= time(16, 0))]
    if day_rth.empty: continue
    
    # ORB (09:30 - 10:00)
    orb_window = day_rth[(day_rth.index.time >= time(9, 30)) & (day_rth.index.time < time(10, 0))]
    if orb_window.empty: continue
    orb_h = orb_window['high'].max()
    orb_l = orb_window['low'].min()
    
    # Trading (From 10:00)
    trading_data = day_rth[day_rth.index.time >= time(10, 0)]
    bars = trading_data.to_dict('records')
    times = trading_data.index
    
    state = "IDLE"
    pos_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_time = None
    
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
            # Next-bar Open + Slippage
            fill = bar['open']
            if pos_type == "Long":
                fill += SLIPPAGE_TICKS * TICK_SIZE
                stop_loss = orb_l
                take_profit = fill + (fill - stop_loss)
            else:
                fill -= SLIPPAGE_TICKS * TICK_SIZE
                stop_loss = orb_h
                take_profit = fill - (stop_loss - fill)
            
            entry_price = fill
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
            else: # Short
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
                    'reason': reason,
                    'entry_time': entry_time,
                    'exit_time': curr_time,
                    'symbol': active_sym
                })
                state = "FINISHED"
                break

# 5. Analysis & Charting
print("Step 5: Generating Final Analysis...")
trades_df = pd.DataFrame(trades)
trades_df['cum_pnl'] = trades_df['pnl_usd'].cumsum()
trades_df['peak'] = trades_df['cum_pnl'].cummax()
trades_df['drawdown'] = trades_df['cum_pnl'] - trades_df['peak']

# Stats
total_pnl = trades_df['pnl_usd'].sum()
win_rate = (trades_df['pnl_usd'] > 0).mean() * 100
pf = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum() / abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())

# Plots
fig = plt.figure(figsize=(15, 12))

# Equity
plt.subplot(3, 1, 1)
plt.plot(pd.to_datetime(trades_df['date']), trades_df['cum_pnl'], color='#2ecc71', linewidth=2)
plt.title(f'Final Master Backtest: NQ 30m ORB (Total PnL: ${total_pnl:,.2f})', fontsize=14)
plt.ylabel('USD PnL')
plt.grid(True, alpha=0.3)

# Drawdown
plt.subplot(3, 1, 2)
plt.fill_between(pd.to_datetime(trades_df['date']), trades_df['drawdown'], 0, color='#e74c3c', alpha=0.3)
plt.title('Drawdown (USD)', fontsize=12)
plt.grid(True, alpha=0.3)

# Monthly Heatmap
trades_df['date_dt'] = pd.to_datetime(trades_df['date'])
trades_df['year'] = trades_df['date_dt'].dt.year
trades_df['month'] = trades_df['date_dt'].dt.month
monthly_pnl = trades_df.groupby(['year', 'month'])['pnl_usd'].sum().unstack()

plt.subplot(3, 1, 3)
sns.heatmap(monthly_pnl, annot=True, fmt=".0f", cmap='RdYlGn', center=0, cbar=False)
plt.title('Monthly PnL Heatmap (USD)', fontsize=12)

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_master_report.png')

# Save CSV
trades_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_master_trades.csv', index=False)

print(f"\nFinal Stats:")
print(f"Total Trades: {len(trades_df)}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Profit Factor: {pf:.2f}")
print(f"Final USD PnL: ${total_pnl:,.2f}")
print("\nRe-run complete. Files saved.")
