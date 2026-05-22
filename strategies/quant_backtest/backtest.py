import os
import sys
import numpy as np
import pandas as pd
from numba import njit
import matplotlib.pyplot as plt

try:
    import databento as db
except ImportError:
    print("Please install databento: pip install databento")
    sys.exit(1)

def load_data(filepath, cached_path="front_month_data.parquet"):
    if os.path.exists(cached_path):
        print(f"Loading cached front-month data from {cached_path}...")
        df = pd.read_parquet(cached_path)
        return df
        
    print(f"Parsing raw databento file {filepath} (This might take a moment)...")
    store = db.DBNStore.from_file(filepath)
    df = store.to_df()
    
    print("Converting timezone to US/Eastern...")
    df = df.tz_convert('America/New_York')
    
    print("Finding the front-month contract per day based on max volume...")
    df['date'] = df.index.date
    daily_vol = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
    idx = daily_vol.groupby(['date'])['volume'].idxmax()
    front_month = daily_vol.loc[idx, ['date', 'symbol']]
    
    print("Filtering data down to continuous front-month timeline...")
    df = df.reset_index().merge(front_month, on=['date', 'symbol'], how='inner')
    df = df.set_index('ts_event').sort_index()
    
    print(f"Saving compiled data to {cached_path}...")
    df.to_parquet(cached_path)
    return df

@njit
def run_backtest_numba(open_p, high_p, low_p, close_p, vol_p, timestamps, dates, hours, mins, tp_size):
    n = len(open_p)
    
    entry_idx_list = []
    exit_idx_list = []
    pos_list = []
    entry_p_list = []
    exit_p_list = []
    pnl_list = []
    
    vwapValue = np.nan
    pSum = 0.0
    vSum = 0.0
    
    orbHighPrice = np.nan
    orbLowPrice = np.nan
    orbRange = 0.0
    
    pendingLong = False
    pendingShort = False
    tradedToday = False
    
    pos_type = 0 # 1 long, -1 short, 0 flat
    entry_price = 0.0
    entry_time_idx = 0
    stop_loss = 0.0
    take_profit = 0.0
    
    for i in range(1, n):
        is_new_day = (dates[i] != dates[i-1])
        
        hlc3 = (high_p[i] + low_p[i] + close_p[i]) / 3.0
        v = vol_p[i]
        
        if is_new_day:
            pSum = hlc3 * v
            vSum = v
            orbHighPrice = np.nan
            orbLowPrice = np.nan
            pendingLong = False
            pendingShort = False
            tradedToday = False
            
            # Force close overnight position
            if pos_type != 0:
                exit_price = open_p[i]
                pnl = (exit_price - entry_price) if pos_type == 1 else (entry_price - exit_price)
                entry_idx_list.append(entry_time_idx)
                exit_idx_list.append(i)
                pos_list.append(pos_type)
                entry_p_list.append(entry_price)
                exit_p_list.append(exit_price)
                pnl_list.append(pnl)
                pos_type = 0
        else:
            pSum += hlc3 * v
            vSum += v
            
        if vSum > 0:
            vwapValue = pSum / vSum
            
        h = hours[i]
        m = mins[i]
        
        # In Session: 09:30 - 09:59 (30 minutes)
        in_session = (h == 9 and 30 <= m)
        
        if in_session:
            if np.isnan(orbHighPrice):
                orbHighPrice = high_p[i]
                orbLowPrice = low_p[i]
            else:
                orbHighPrice = max(orbHighPrice, high_p[i])
                orbLowPrice = min(orbLowPrice, low_p[i])
            orbRange = orbHighPrice - orbLowPrice
            
        out_of_session = (not in_session) and (h >= 10)
        
        if out_of_session and (not tradedToday) and (not np.isnan(orbHighPrice)):
            if high_p[i] > orbHighPrice:
                pendingLong = True
            if low_p[i] < orbLowPrice:
                pendingShort = True
                
        # Handle Open Positions
        if pos_type != 0:
            time_hit = (timestamps[i] - timestamps[entry_time_idx]) >= 23400000000000 # ns
            is_market_close = (h == 16 and m >= 0)
            
            exited = False
            exit_price = 0.0
            
            if time_hit or is_market_close:
                exit_price = open_p[i]
                exited = True
            else:
                if pos_type == 1:
                    if low_p[i] <= stop_loss:
                        exit_price = stop_loss
                        exited = True
                    elif high_p[i] >= take_profit:
                        exit_price = take_profit
                        exited = True
                elif pos_type == -1:
                    if high_p[i] >= stop_loss:
                        exit_price = stop_loss
                        exited = True
                    elif low_p[i] <= take_profit:
                        exit_price = take_profit
                        exited = True
                        
            if exited:
                pnl = (exit_price - entry_price) if pos_type == 1 else (entry_price - exit_price)
                entry_idx_list.append(entry_time_idx)
                exit_idx_list.append(i)
                pos_list.append(pos_type)
                entry_p_list.append(entry_price)
                exit_p_list.append(exit_price)
                pnl_list.append(pnl - 0.205) # ~4.10 USD RT Commission expressed in NQ points
                pos_type = 0
                
        # Search For Entry if flat
        if pos_type == 0 and out_of_session and (not tradedToday):
            # Allowed entry window: 09:30 to 12:00 EDT
            in_trade_time = (h == 9 and m >= 30) or (h == 10) or (h == 11) or (h == 12 and m == 0)
            
            if in_trade_time:
                if pendingLong:
                    if low_p[i] <= vwapValue <= high_p[i]:
                        pos_type = 1
                        entry_price = vwapValue
                    elif high_p[i] < vwapValue:
                        pos_type = 1
                        entry_price = open_p[i]
                        
                    if pos_type == 1:
                        entry_time_idx = i
                        stop_loss = orbLowPrice - 0.25 # Minor simulated slippage on stop
                        take_profit = orbHighPrice + (orbRange * tp_size)
                        tradedToday = True
                        pendingLong = False
                        
                if pendingShort and pos_type == 0:
                    if low_p[i] <= vwapValue <= high_p[i]:
                        pos_type = -1
                        entry_price = vwapValue
                    elif low_p[i] > vwapValue:
                        pos_type = -1
                        entry_price = open_p[i]
                        
                    if pos_type == -1:
                        entry_time_idx = i
                        stop_loss = orbHighPrice + 0.25
                        take_profit = orbLowPrice - (orbRange * tp_size)
                        tradedToday = True
                        pendingShort = False
                        
    return entry_idx_list, exit_idx_list, pos_list, entry_p_list, exit_p_list, pnl_list

def main():
    filepath = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn"
    cached_path = "front_month_data.parquet"
    
    df = load_data(filepath, cached_path)
    print(f"Data shape after preparation: {df.shape}")
    
    open_p = df['open'].values.astype(np.float64)
    high_p = df['high'].values.astype(np.float64)
    low_p = df['low'].values.astype(np.float64)
    close_p = df['close'].values.astype(np.float64)
    vol_p = df['volume'].values.astype(np.float64)
    
    timestamps = df.index.values.astype(np.int64)
    date_ints = df.index.strftime('%Y%m%d').astype(np.int32).values
    hours = df.index.hour.values.astype(np.int32)
    mins = df.index.minute.values.astype(np.int32)
    
    tp_size = 1.0 
    
    print("Running Numba backtest engine...")
    res = run_backtest_numba(open_p, high_p, low_p, close_p, vol_p, timestamps, date_ints, hours, mins, tp_size)
    
    entry_idx, exit_idx, positions, entry_p, exit_p, pnl = res
    print(f"Total Trades Engine Triggered: {len(pnl)}")
    
    if len(pnl) == 0:
        print("No trades executed.")
        return
        
    pnl_array = np.array(pnl)
    # NQ futures $20 per point multiplier
    pnl_usd = pnl_array * 20
    
    cumulative_pnl = np.cumsum(pnl_usd)
    win_rate = np.mean(pnl_array > 0)
    total_pnl = cumulative_pnl[-1]
    
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = running_max - cumulative_pnl
    max_dd = np.max(drawdowns)
    
    print("-" * 30)
    print(f"Performance Summary (tp_size={tp_size})")
    print("-" * 30)
    print(f"Total PnL:     ${total_pnl:,.2f}")
    print(f"Win Rate:      {win_rate*100:.2f}%")
    print(f"Max Drawdown:  ${max_dd:,.2f}")
    
    plt.figure(figsize=(10, 5))
    plt.plot(cumulative_pnl, color='dodgerblue')
    plt.title(f"30m ORB VWAP Equity Curve (Total PnL: ${total_pnl:,.0f})", fontsize=14, pad=10)
    plt.xlabel("Trade Number", fontsize=12)
    plt.ylabel("Cumulative PnL (USD)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.fill_between(range(len(cumulative_pnl)), cumulative_pnl, 0, alpha=0.1, color='dodgerblue')
    plt.tight_layout()
    plt.savefig("equity_curve.png", dpi=150)
    print("Saved equity curve to equity_curve.png")

if __name__ == '__main__':
    main()
