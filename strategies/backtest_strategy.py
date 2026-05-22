import pandas as pd
import numpy as np
import databento as db
import vectorbt as vbt
from numba import njit
import sys
import os

dbn_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

print("Loading databento data... This may take a minute.")
try:
    store = db.DBNStore.from_file(dbn_path)
    df = store.to_df()
except Exception as e:
    print(f"Error loading databento file: {e}")
    sys.exit(1)

# Helper for daily contract filtering
def get_daily_top_instrument(group):
    volume_sums = group.groupby('instrument_id')['volume'].sum()
    if volume_sums.empty: return group
    return group[group['instrument_id'] == volume_sums.idxmax()]

# ATR calculation BEFORE 2021 filtering to ensure data buffer
print("Pre-calculating 7-day ATR (True Range) with pre-2021 buffer...")
df_full = store.to_df()
if not isinstance(df_full.index, pd.DatetimeIndex):
    df_full.index = pd.to_datetime(df_full.index)
if df_full.index.tz is None:
    df_full.index = df_full.index.tz_localize('UTC')
df_full.index = df_full.index.tz_convert('America/New_York')

# Filter for top instrument daily
df_full_top = df_full.groupby(df_full.index.date, group_keys=False).apply(get_daily_top_instrument)

daily_full = df_full_top.resample('D').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
daily_full['prev_close'] = daily_full['close'].shift(1)
daily_full['tr'] = np.maximum(daily_full['high'] - daily_full['low'], 
                             np.maximum(np.abs(daily_full['high'] - daily_full['prev_close']), 
                                        np.abs(daily_full['low'] - daily_full['prev_close'])))
daily_full['atr7'] = daily_full['tr'].rolling(7).mean().shift(1) # Shift to be causal

# Filter simulation data (2021+)
print("Filtering simulation data (2021+)...")
df = df_full_top[df_full_top.index >= '2021-01-01'].copy()

# Filter RTH (09:30 - 16:00 ET) AFTER ATR calculation
rth_mask = (df.index.time >= pd.to_datetime('09:30:00').time()) & (df.index.time <= pd.to_datetime('16:00:00').time())
df = df[rth_mask].copy()

# Filter out bad ticks
df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]

df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
df = df.sort_index()

open_arr = df['open'].values
high_arr = df['high'].values
low_arr = df['low'].values
close_arr = df['close'].values
vol_arr = df['volume'].values

dates = df.index.date
unique_dates = np.unique(dates)
day_indices = np.searchsorted(unique_dates, dates)

minutes_from_930 = (df.index.hour - 9) * 60 + df.index.minute - 30
time_arr = minutes_from_930.values

@njit
def get_svp_val(highs, lows, vols, start_idx, end_idx, tick_size=0.25):
    min_price = np.min(lows[start_idx:end_idx+1])
    max_price = np.max(highs[start_idx:end_idx+1])
    
    num_bins = int(np.ceil((max_price - min_price) / tick_size)) + 1
    profile = np.zeros(num_bins)
    
    for i in range(start_idx, end_idx+1):
        h = highs[i]
        l = lows[i]
        v = vols[i]
        # Distribute volume equally across ticks in the bar
        ticks_in_bar = max(1, int(np.round((h - l) / tick_size)) + 1)
        v_per_tick = v / ticks_in_bar
        
        start_bin = int(np.round((l - min_price) / tick_size))
        end_bin = int(np.round((h - min_price) / tick_size))
        
        for b in range(start_bin, end_bin + 1):
            if b < num_bins:
                profile[b] += v_per_tick
                
    poc_bin = np.argmax(profile)
    total_vol = np.sum(profile)
    target_vol = total_vol * 0.70
    
    current_vol = profile[poc_bin]
    upper_bin = poc_bin
    lower_bin = poc_bin
    
    while current_vol < target_vol:
        vol_up = profile[upper_bin + 1] if upper_bin + 1 < num_bins else 0
        vol_down = profile[lower_bin - 1] if lower_bin - 1 >= 0 else 0
        
        if vol_up == 0 and vol_down == 0:
            break
            
        if vol_up >= vol_down:
            upper_bin += 1
            current_vol += vol_up
        else:
            lower_bin -= 1
            current_vol += vol_down
            
    val_price = min_price + lower_bin * tick_size
    return val_price

def run_backtest(open_arr, high_arr, low_arr, close_arr, vol_arr, day_indices, time_arr, max_risk=9999.0, breakout_tf=1, use_slope=False, rr_ratio=3.0, atr_tp_arr=None):
    n = len(open_arr)
    entries = np.zeros(n)
    exits = np.zeros(n)
    in_trade = False
    stop_loss = 0.0
    take_profit = 0.0
    entry_price = 0.0
    current_day = -1
    orb_high = -1.0
    orb_low = 999999.0
    breakout_confirmed = False
    trade_taken_today = False
    cum_vol = 0.0
    cum_pv = 0.0
    vwap_history = np.zeros(n)
    session_start_idx = 0
    vwap_offset = 1.0 
    
    for i in range(n):
        day = day_indices[i]
        t = time_arr[i]
        
        if day != current_day:
            in_trade = False
            current_day = day
            orb_high = -1.0
            orb_low = 999999.0
            breakout_confirmed = False
            trade_taken_today = False
            cum_vol = 0.0
            cum_pv = 0.0
            session_start_idx = i
            vwap_history[i] = open_arr[i]
            
        if in_trade and t >= 385:
            exits[i] = close_arr[i]
            in_trade = False
            continue
            
        if in_trade:
            hit_tp = high_arr[i] >= take_profit
            hit_sl = low_arr[i] <= stop_loss
            if hit_tp and hit_sl: exits[i] = stop_loss; in_trade = False
            elif hit_sl: exits[i] = stop_loss; in_trade = False
            elif hit_tp: exits[i] = take_profit; in_trade = False
            continue

        can_enter = (not trade_taken_today) and breakout_confirmed and (not in_trade) and (t <= 180)
        
        if use_slope and can_enter:
            lookback_idx = max(session_start_idx, i - 11)
            if vwap_history[i-1] <= vwap_history[lookback_idx]:
                can_enter = False 

        if can_enter:
            limit_price = vwap_history[i-1] + vwap_offset
            if low_arr[i] <= limit_price:
                entry_limit = min(limit_price, open_arr[i])
                val = get_svp_val(high_arr, low_arr, vol_arr, session_start_idx, i - 1, tick_size=0.25)
                if val < entry_limit:
                    risk = entry_limit - val
                    if risk < 2.0: risk = 2.0
                    if risk <= max_risk:
                        in_trade = True
                        trade_taken_today = True
                        entries[i] = entry_limit
                        stop_loss = val
                        
                        if atr_tp_arr is not None:
                            # Use ATR-based dynamic TP
                            take_profit = entry_limit + atr_tp_arr[i]
                        else:
                            # Use Fixed RR TP
                            take_profit = entry_limit + risk * rr_ratio
                    else:
                        trade_taken_today = True 

        typ_price = (high_arr[i] + low_arr[i] + close_arr[i]) / 3.0
        cum_pv += typ_price * vol_arr[i]
        cum_vol += vol_arr[i]
        vwap_history[i] = cum_pv / cum_vol if cum_vol > 0 else typ_price
        
        if t <= 14:
            if high_arr[i] > orb_high: orb_high = high_arr[i]
            if low_arr[i] < orb_low: orb_low = low_arr[i]
        
        if not breakout_confirmed and t > 14:
            if breakout_tf == 5:
                if (t + 1) % 5 == 0:
                    if close_arr[i] > orb_high: breakout_confirmed = True
            else:
                if close_arr[i] > orb_high: breakout_confirmed = True

    return entries, exits

# Map daily ATR7 back to 1-minute bars
df_temp = df.copy()
df_temp['date_norm'] = df_temp.index.normalize().tz_localize(None)
daily_full.index = daily_full.index.normalize().tz_localize(None)
df_temp = df_temp.merge(daily_full[['atr7']], left_on='date_norm', right_index=True, how='left')
atr7_values = df_temp['atr7'].fillna(100.0).values # Default 100 points if unknown

def calculate_stats(entries, exits, df):
    pnls = []
    entry_times = []
    current_entry_price = 0.0
    current_entry_time = None
    for i in range(len(df)):
        if entries[i] > 0: current_entry_price = entries[i]; current_entry_time = df.index[i]
        if exits[i] > 0 and current_entry_time is not None and current_entry_price != 0:
            pnls.append(exits[i] - current_entry_price)
            entry_times.append(current_entry_time)
            current_entry_price = 0.0; current_entry_time = None
    if len(pnls) == 0: return None
    pnls = np.array(pnls); dollar_pnls = pnls * 20.0 - 4.0
    wins = dollar_pnls[dollar_pnls > 0]; losses = dollar_pnls[dollar_pnls <= 0]
    cum_pnl = np.cumsum(dollar_pnls); peak = np.maximum.accumulate(cum_pnl); dd = np.max(peak - cum_pnl)
    trades_df = pd.DataFrame({'Time': entry_times, 'PnL': dollar_pnls}).set_index('Time')
    daily_pnl = trades_df.resample('D')['PnL'].sum()
    sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252) if daily_pnl.std() != 0 else 0
    return {'Profit': np.sum(dollar_pnls), 'Trades': len(dollar_pnls), 'WinRate': len(wins)/len(dollar_pnls)*100, 'PF': abs(wins.sum()/losses.sum()) if len(losses)>0 else 99, 'MaxDD': dd, 'Sharpe': sharpe}

print("\nComparing Strategy Target Methods (Sensitivity Analysis)...")
methods = [
    {"label": "Fixed RR 1:1", "rr": 1.0, "atr_mult": 0.0},
    {"label": "Fixed RR 1:2", "rr": 2.0, "atr_mult": 0.0},
    {"label": "Fixed RR 1:3", "rr": 3.0, "atr_mult": 0.0},
    {"label": "ATR 0.1x", "rr": 0.0, "atr_mult": 0.1},
    {"label": "ATR 0.2x", "rr": 0.0, "atr_mult": 0.2},
    {"label": "ATR 0.3x", "rr": 0.0, "atr_mult": 0.3},
    {"label": "ATR 0.4x", "rr": 0.0, "atr_mult": 0.4},
    {"label": "ATR 0.5x", "rr": 0.0, "atr_mult": 0.5},
    {"label": "ATR 0.6x", "rr": 0.0, "atr_mult": 0.6},
]

results = []
all_trades = {}

for m in methods:
    if m['atr_mult'] > 0:
        tp_arr = atr7_values * m['atr_mult']
        ent, ex = run_backtest(open_arr, high_arr, low_arr, close_arr, vol_arr, day_indices, time_arr, max_risk=60.0, rr_ratio=0.0, atr_tp_arr=tp_arr)
    else:
        ent, ex = run_backtest(open_arr, high_arr, low_arr, close_arr, vol_arr, day_indices, time_arr, max_risk=60.0, rr_ratio=m['rr'], atr_tp_arr=None)
        
    stats = calculate_stats(ent, ex, df)
    if stats:
        print(f"\n[{m['label']}]")
        for k, v in stats.items(): print(f"  {k}: {v:,.2f}")
        stats['label'] = m['label']
        results.append(stats)
        
        # Store trades for plotting
        pnls = []
        entry_times = []
        current_entry_price = 0.0
        current_entry_time = None
        for i in range(len(df)):
            if ent[i] > 0: current_entry_price = ent[i]; current_entry_time = df.index[i]
            if ex[i] > 0 and current_entry_time is not None and current_entry_price != 0:
                pnls.append(ex[i] - current_entry_price)
                entry_times.append(current_entry_time)
                current_entry_price = 0.0; current_entry_time = None
        
        trades_df = pd.DataFrame({'Time': entry_times, 'PnL': np.array(pnls) * 20.0 - 4.0}).set_index('Time')
        all_trades[m['label']] = trades_df

# Save comparison results
with open('atr_vs_fixed_comparison.txt', 'w') as f:
    f.write("Strategy Comparison: Fixed RR 1:1 vs ATR Targets\n")
    f.write("="*50 + "\n")
    for res in results:
        f.write(f"\n[{res['label']}]\n")
        f.write(f"  Profit: ${res['Profit']:,.2f}\n")
        f.write(f"  Trades: {res['Trades']}\n")
        f.write(f"  Win Rate: {res['WinRate']:.2f}%\n")
        f.write(f"  Profit Factor: {res['PF']:.2f}\n")
        f.write(f"  Sharpe Ratio: {res['Sharpe']:.2f}\n")
        f.write(f"  Max Drawdown: ${res['MaxDD']:,.2f}\n")

# Plot Equity Curves
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 7))
for label, trades in all_trades.items():
    equity = trades['PnL'].cumsum()
    plt.plot(equity.index, equity.values, label=label)

plt.title('NQ 15m ORB: Fixed RR 1:1 vs ATR Targets')
plt.xlabel('Date')
plt.ylabel('Cumulative Profit ($)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('equity_curves_comparison.png')
print("\nEquity curves saved to equity_curves_comparison.png")

# Best method summary
best_sharpe = max(results, key=lambda x: x['Sharpe'])
print(f"\n>>> Best Sharpe: {best_sharpe['label']} ({best_sharpe['Sharpe']:.2f})")





