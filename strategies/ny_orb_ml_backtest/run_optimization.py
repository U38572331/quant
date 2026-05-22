import numpy as np
import pandas as pd
from numba import njit, prange
import time
import os
import itertools
import warnings
warnings.filterwarnings('ignore')

@njit(parallel=True)
def run_grid_search(ny_date, ny_time, high, low, close, vwap, orb_mins_arr, rr_long_arr, rr_short_arr):
    n_bars = len(close)
    n_params = len(orb_mins_arr)
    
    results_trades = np.zeros(n_params, dtype=np.int32)
    results_wins = np.zeros(n_params, dtype=np.int32)
    results_gross_win = np.zeros(n_params, dtype=np.float64)
    results_gross_loss = np.zeros(n_params, dtype=np.float64)
    
    for p in prange(n_params):
        orb_mins = orb_mins_arr[p]
        rr_long = rr_long_arr[p]
        rr_short = rr_short_arr[p]
        
        # Calculate ORB end time in HHMM format
        orb_end_time = 930 + orb_mins
        if (orb_end_time % 100) >= 60:
            orb_end_time = (orb_end_time // 100 + 1) * 100 + (orb_end_time % 100 - 60)
        
        position = 0
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        
        orb_high = -1.0
        orb_low = 999999.0
        traded_today = False
        current_day = -1
        
        trades = 0
        wins = 0
        gross_win = 0.0
        gross_loss = 0.0
        
        for i in range(n_bars):
            d = ny_date[i]
            t = ny_time[i]
            
            if d != current_day:
                current_day = d
                traded_today = False
                orb_high = -1.0
                orb_low = 999999.0
                if position != 0:
                    pnl = (close[i] - entry_price) * position
                    trades += 1
                    if pnl > 0:
                        wins += 1
                        gross_win += pnl
                    else:
                        gross_loss -= pnl
                    position = 0
            
            if 930 <= t < orb_end_time:
                if high[i] > orb_high: orb_high = high[i]
                if low[i] < orb_low: orb_low = low[i]
            
            if position != 0:
                if t >= 1555:
                    pnl = (close[i] - entry_price) * position
                    trades += 1
                    if pnl > 0:
                        wins += 1
                        gross_win += pnl
                    else:
                        gross_loss -= pnl
                    position = 0
                else:
                    hit_sl = False
                    hit_tp = False
                    
                    if position == 1:
                        if low[i] <= stop_loss: hit_sl = True
                        if high[i] >= take_profit: hit_tp = True
                        
                        if hit_sl and hit_tp:
                            pnl = stop_loss - entry_price
                            trades += 1
                            gross_loss -= pnl
                            position = 0
                        elif hit_sl:
                            pnl = stop_loss - entry_price
                            trades += 1
                            gross_loss -= pnl
                            position = 0
                        elif hit_tp:
                            pnl = take_profit - entry_price
                            trades += 1
                            wins += 1
                            gross_win += pnl
                            position = 0
                    
                    elif position == -1:
                        if high[i] >= stop_loss: hit_sl = True
                        if low[i] <= take_profit: hit_tp = True
                        
                        if hit_sl and hit_tp:
                            pnl = entry_price - stop_loss
                            trades += 1
                            gross_loss -= pnl
                            position = 0
                        elif hit_sl:
                            pnl = entry_price - stop_loss
                            trades += 1
                            gross_loss -= pnl
                            position = 0
                        elif hit_tp:
                            pnl = entry_price - take_profit
                            trades += 1
                            wins += 1
                            gross_win += pnl
                            position = 0

            if position == 0 and not traded_today and orb_high > 0 and t >= orb_end_time and t < 1555:
                # 5-minute candle close confirmation + VWAP directional filter
                if t % 5 == 4:
                    if close[i] > orb_high and close[i] > vwap[i]:
                        risk = close[i] - orb_low
                        if risk > 0:
                            position = 1
                            entry_price = close[i]
                            stop_loss = orb_low
                            take_profit = close[i] + risk * rr_long
                            traded_today = True
                    elif close[i] < orb_low and close[i] < vwap[i]:
                        risk = orb_high - close[i]
                        if risk > 0:
                            position = -1
                            entry_price = close[i]
                            stop_loss = orb_high
                            take_profit = close[i] - risk * rr_short
                            traded_today = True

        results_trades[p] = trades
        results_wins[p] = wins
        results_gross_win[p] = gross_win
        results_gross_loss[p] = gross_loss

    return results_trades, results_wins, results_gross_win, results_gross_loss

def main():
    print("Loading data...")
    # Read the data
    df = pd.read_parquet(r"..\data\nq_pro.parquet", columns=['ts_event', 'symbol', 'high', 'low', 'close', 'vwap'])
    
    # Filter out spreads
    df = df[~df['symbol'].str.contains('-')].copy()
    
    # Process timestamps
    print("Converting timezone...")
    df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')
    
    # Filter last 6 years (2019-10 to 2025-10)
    print("Filtering 6 years of data...")
    start_date = pd.Timestamp('2019-10-01', tz='America/New_York')
    df = df[df['ts_event'] >= start_date].copy()
    
    # Create fast numeric columns for numba
    df['ny_date'] = df['ts_event'].dt.year * 10000 + df['ts_event'].dt.month * 100 + df['ts_event'].dt.day
    df['ny_time'] = df['ts_event'].dt.hour * 100 + df['ts_event'].dt.minute
    
    # Filter RTH + little padding (0930 to 1600)
    df = df[(df['ny_time'] >= 930) & (df['ny_time'] <= 1600)].reset_index(drop=True)
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    vwap = df['vwap'].values.astype(np.float64)
    ny_date = df['ny_date'].values
    ny_time = df['ny_time'].values
    
    print(f"Data ready. Total bars: {len(close)}")
    
    # Define parameters
    orb_mins_options = [25, 30, 60]
    rr_options = np.arange(0.5, 5.1, 0.1)
    
    # We will test symmetric RR and combinations where long RR != short RR.
    # To save time, we will test symmetric RR and a subset of combinations.
    # Let's test symmetric only first, or just all permutations if fast enough.
    # 3 * 46 * 46 = 6348 combinations
    combinations = list(itertools.product(orb_mins_options, rr_options, rr_options))
    orb_mins_arr = np.array([c[0] for c in combinations], dtype=np.int32)
    rr_long_arr = np.array([c[1] for c in combinations], dtype=np.float64)
    rr_short_arr = np.array([c[2] for c in combinations], dtype=np.float64)
    
    print(f"Running grid search for {len(combinations)} combinations...")
    start_t = time.time()
    
    trades, wins, gross_win, gross_loss = run_grid_search(
        ny_date, ny_time, high, low, close, vwap,
        orb_mins_arr, rr_long_arr, rr_short_arr
    )
    
    print(f"Optimization completed in {time.time() - start_t:.2f} seconds.")
    
    # Analyze results
    results = []
    for i in range(len(combinations)):
        t = trades[i]
        if t == 0: continue
        w = wins[i]
        win_rate = w / t
        pf = gross_win[i] / gross_loss[i] if gross_loss[i] > 0 else 999.0
        net_profit = gross_win[i] - gross_loss[i]
        
        results.append({
            'orb': orb_mins_arr[i],
            'rr_long': rr_long_arr[i],
            'rr_short': rr_short_arr[i],
            'trades': t,
            'win_rate': win_rate,
            'pf': pf,
            'net_profit': net_profit
        })
    
    res_df = pd.DataFrame(results)
    res_df.to_csv("optimization_results.csv", index=False)
    print("Saved optimization_results.csv")
    
    # Filter by user conditions: Win Rate >= 65%, PF >= 1.5
    valid_df = res_df[(res_df['win_rate'] >= 0.65) & (res_df['pf'] >= 1.5)]
    print(f"Combinations meeting criteria (WR>=0.65, PF>=1.5): {len(valid_df)}")
    
    if len(valid_df) > 0:
        best = valid_df.sort_values('net_profit', ascending=False).iloc[0]
        print("\nBest Parameters among valid:")
        print(best)
    else:
        print("\nNo parameters met the strict criteria. Showing Top 5 by Profit Factor:")
        best = res_df[res_df['trades'] > 100].sort_values('pf', ascending=False).head(5)
        print(best)

if __name__ == "__main__":
    main()
