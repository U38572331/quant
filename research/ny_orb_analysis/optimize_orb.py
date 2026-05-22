import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Configuration
DATA_FILE = r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv'
ARTIFACTS_DIR = r'C:\Users\user\.gemini\antigravity\brain\19288795-ea17-435e-a45c-dc9b64c40984'

# 5-Minute ORB Settings
ORB_START_TIME = '09:30'
ORB_END_TIME = '09:35' # 5 Minute Duration
SESSION_END_TIME = '16:00'

def load_and_prep_data(filepath):
    print("Loading data...")
    df = pd.read_csv(filepath)
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df['dt_ny'] = df['ts_event'].dt.tz_convert('US/Eastern')
    return df

def select_active_contract(df):
    print("Selecting active contracts...")
    df['date_ny'] = df['dt_ny'].dt.date
    daily_vol = df.groupby(['date_ny', 'symbol'])['volume'].sum().reset_index()
    max_vol_idx = daily_vol.groupby(['date_ny'])['volume'].idxmax()
    active_contracts = daily_vol.loc[max_vol_idx, ['date_ny', 'symbol']]
    active_contracts.rename(columns={'symbol': 'active_symbol'}, inplace=True)
    df_merged = pd.merge(df, active_contracts, on='date_ny', how='left')
    df_active = df_merged[df_merged['symbol'] == df_merged['active_symbol']].copy()
    return df_active

def get_trades(df):
    print("Identifying Trades...")
    trades = []
    
    df.set_index('dt_ny', inplace=True)
    df.sort_index(inplace=True)
    df['date_group'] = df.index.date
    grouped = df.groupby('date_group')
    
    for day, day_df in grouped:
        day_str = str(day)
        try:
            orb_start = pd.Timestamp(f"{day_str} {ORB_START_TIME}").tz_localize('US/Eastern')
            orb_end = pd.Timestamp(f"{day_str} {ORB_END_TIME}").tz_localize('US/Eastern')
            session_end = pd.Timestamp(f"{day_str} {SESSION_END_TIME}").tz_localize('US/Eastern')
        except:
            continue
            
        orb_data = day_df[(day_df.index >= orb_start) & (day_df.index < orb_end)]
        if orb_data.empty: continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_width = orb_high - orb_low
        
        if orb_width == 0: continue
            
        exec_data = day_df[(day_df.index >= orb_end) & (day_df.index <= session_end)]
        if exec_data.empty: continue
            
        # Vectorized Breakout Detection
        long_breakouts = exec_data[exec_data['high'] > orb_high]
        short_breakouts = exec_data[exec_data['low'] < orb_low]
        
        first_long = long_breakouts.index[0] if not long_breakouts.empty else pd.NaT
        first_short = short_breakouts.index[0] if not short_breakouts.empty else pd.NaT
        
        if pd.isna(first_long) and pd.isna(first_short):
            continue
            
        if not pd.isna(first_long) and (pd.isna(first_short) or first_long < first_short):
            direction = 'long'
            entry_price = orb_high
            stop_price = orb_low
            entry_time = first_long
        else:
            direction = 'short'
            entry_price = orb_low
            stop_price = orb_high
            entry_time = first_short
            
        # Get price path after entry to check outcomes
        path = exec_data[exec_data.index >= entry_time].copy()
        
        trades.append({
            'date': day,
            'direction': direction,
            'entry_price': entry_price,
            'stop_price': stop_price,
            'orb_width': orb_width,
            'path_highs': path['high'].values,
            'path_lows': path['low'].values
        })
        
    return trades

def optimize_targets(trades):
    print("Running Optimization Sweep...")
    
    # 1. Fixed Points Optimization
    point_targets = np.arange(10, 105, 5) # 10 to 100
    point_results = []
    
    for tgt in point_targets:
        wins = 0
        total_pnl = 0
        
        for t in trades:
            risk = t['orb_width']
            
            # Outcome Logic
            # Conservative: If high >= target AND low <= stop in same bar, assume loss first?
            # We assume bar 0 is entry bar.
            # If entry bar hits target: Win. (Optimistic? Maybe, but assumes stop limit fills)
            # If entry bar hits stop: Loss.
            
            # Simple simulation: iterate through path
            trade_pnl = -risk # Default is loss (hit stop)
            
            for i in range(len(t['path_highs'])):
                h = t['path_highs'][i]
                l = t['path_lows'][i]
                
                # Check for stop first (Conservative for backtesting)
                hit_stop = False
                hit_target = False
                
                if t['direction'] == 'long':
                    if l <= t['stop_price']: hit_stop = True
                    if h >= t['entry_price'] + tgt: hit_target = True
                else:
                    if h >= t['stop_price']: hit_stop = True
                    if l <= t['entry_price'] - tgt: hit_target = True
                
                if hit_stop and hit_target:
                    # Both in same bar. Assume Loss if i > 0.
                    # If i == 0 (entry bar), tough call. Assume loss.
                    trade_pnl = -risk
                    break
                elif hit_stop:
                    trade_pnl = -risk
                    break
                elif hit_target:
                    trade_pnl = tgt
                    wins += 1
                    break
            
            total_pnl += trade_pnl
            
        n = len(trades)
        win_rate = (wins / n) * 100 if n > 0 else 0
        expectancy = total_pnl / n if n > 0 else 0
        
        point_results.append({
            'Target': tgt,
            'WinRate': win_rate,
            'Expectancy': expectancy,
            'TotalPoints': total_pnl
        })
        
    # 2. R-Multiple Optimization
    r_targets = np.arange(0.5, 5.5, 0.5)
    r_results = []
    
    for r in r_targets:
        wins = 0
        total_points = 0
        
        for t in trades:
            risk = t['orb_width']
            tgt_pts = r * risk
            
            trade_pnl = -risk # Default loss
            
            for i in range(len(t['path_highs'])):
                h = t['path_highs'][i]
                l = t['path_lows'][i]
                
                hit_stop = False
                hit_target = False
                
                if t['direction'] == 'long':
                    if l <= t['stop_price']: hit_stop = True
                    if h >= t['entry_price'] + tgt_pts: hit_target = True
                else:
                    if h >= t['stop_price']: hit_stop = True
                    if l <= t['entry_price'] - tgt_pts: hit_target = True
                
                if hit_stop and hit_target:
                    trade_pnl = -risk
                    break
                elif hit_stop:
                    trade_pnl = -risk
                    break
                elif hit_target:
                    trade_pnl = tgt_pts
                    wins += 1
                    break
            
            total_points += trade_pnl
            
        n = len(trades)
        win_rate = (wins / n) * 100 if n > 0 else 0
        # Expectancy in R-units
        # E = (Win% * R) - (Loss% * 1)
        expectancy_r = ((wins/n) * r) - ((1 - wins/n) * 1)
        
        r_results.append({
            'Target_R': r,
            'WinRate': win_rate,
            'Expectancy_R': expectancy_r,
            'TotalPoints': total_points
        })

    return pd.DataFrame(point_results), pd.DataFrame(r_results)

def plot_results(pt_df, r_df):
    print("Generating Optimization Charts...")
    
    # Points Chart
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    color = 'tab:blue'
    ax1.set_xlabel('Fixed Target (Points)')
    ax1.set_ylabel('Expectancy (Points per Trade)', color=color)
    ax1.plot(pt_df['Target'], pt_df['Expectancy'], color=color, marker='o')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True)
    
    ax2 = ax1.twinx()
    color = 'tab:orange'
    ax2.set_ylabel('Win Rate (%)', color=color)
    ax2.plot(pt_df['Target'], pt_df['WinRate'], color=color, linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('Optimization: Fixed Point Targets (5-min ORB)')
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'opt_best_points_5m.png'))
    plt.close()
    
    # R-Multiple Chart
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    color = 'tab:green'
    ax1.set_xlabel('Target (R-Multiple)')
    ax1.set_ylabel('Expectancy (R per Trade)', color=color)
    ax1.plot(r_df['Target_R'], r_df['Expectancy_R'], color=color, marker='o')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True)
    
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Total Profit (Points)', color=color)
    ax2.plot(r_df['Target_R'], r_df['TotalPoints'], color=color, linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('Optimization: R-Multiple Targets (5-min ORB)')
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'opt_best_rr_5m.png'))
    plt.close()

def main():
    if not os.path.exists(DATA_FILE):
        return
        
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    trades = get_trades(df_active)
    
    if not trades:
        print("No trades found.")
        return
        
    pt_df, r_df = optimize_targets(trades)
    
    print("\n--- Top Fixed Point Targets ---")
    print(pt_df.sort_values(by='Expectancy', ascending=False).head(5))
    
    print("\n--- Top R-Multiple Targets ---")
    print(r_df.sort_values(by='Expectancy_R', ascending=False).head(5))
    
    plot_results(pt_df, r_df)
    
    pt_df.to_csv(os.path.join(ARTIFACTS_DIR, 'opt_points_5m.csv'), index=False)
    r_df.to_csv(os.path.join(ARTIFACTS_DIR, 'opt_rr_5m.csv'), index=False)

if __name__ == "__main__":
    main()
