import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Configuration
DATA_FILE = r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv'
ARTIFACTS_DIR = r'C:\Users\user\.gemini\antigravity\brain\19288795-ea17-435e-a45c-dc9b64c40984'

# 15-Minute ORB Settings
ORB_START_TIME = '09:30'
ORB_END_TIME = '09:45'
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

def get_trades(df, trigger_type='1m_close'):
    print(f"Identifying Trades ({trigger_type})...")
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
        
        # Trigger Logic
        entry_time = None
        direction = None
        entry_price = None
        stop_price = None
        
        if trigger_type == '1m_close':
            # Check 1m closes
            # First candle to close outside range
            # Note: exec_data is 1m data
            long_condition = exec_data['close'] > orb_high
            short_condition = exec_data['close'] < orb_low
            
            first_long = long_condition.idxmax() if long_condition.any() else pd.NaT
            first_short = short_condition.idxmax() if short_condition.any() else pd.NaT
            
            # Logic to pick first valid signal
            # idxmax returns first True index. If none match, handled by check.
            # But if no matches, idxmax returns first index? No, need to check .any()
            
            # Refined check
            has_long = long_condition.any()
            has_short = short_condition.any()
            
            valid_long = first_long if has_long else pd.NaT
            valid_short = first_short if has_short else pd.NaT
            
            if pd.isna(valid_long) and pd.isna(valid_short):
                continue
                
            if not pd.isna(valid_long) and (pd.isna(valid_short) or valid_long < valid_short):
                direction = 'long'
                entry_time = valid_long
                entry_price = exec_data.loc[valid_long]['close'] # Entry at close
                stop_price = orb_low
            elif not pd.isna(valid_short):
                direction = 'short'
                entry_time = valid_short
                entry_price = exec_data.loc[valid_short]['close']
                stop_price = orb_high
                
        elif trigger_type == '5m_close':
            # Resample execution data to 5m bars
            # Offset to align with ORB end (e.g. 09:45, 09:50)
            # Default resample '5T' creates bins 09:45-09:50 labeled 09:45.
            # Close of that bar is known at 09:50? No, 'close' depends on label.
            # Pandas default: label='left', closed='left'. 
            # 09:45 bar covers 09:45:00 - 09:49:59. Close is at 09:49:59.
            # We want to check this close.
            
            resampled = exec_data.resample('5min', closed='left', label='left').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            
            long_condition = resampled['close'] > orb_high
            short_condition = resampled['close'] < orb_low
            
            has_long = long_condition.any()
            has_short = short_condition.any()
            
            valid_long = long_condition.idxmax() if has_long else pd.NaT
            valid_short = short_condition.idxmax() if has_short else pd.NaT
            
            if pd.isna(valid_long) and pd.isna(valid_short):
                continue
                
            if not pd.isna(valid_long) and (pd.isna(valid_short) or valid_long < valid_short):
                direction = 'long'
                entry_time = valid_long # This is the label (e.g. 09:45), signal valid at end of bar
                # Entry price is close of that 5m bar
                entry_price = resampled.loc[valid_long]['close']
                stop_price = orb_low
                # Actual execution starts NEXT bar or immediate?
                # We assume immediate entry at close price.
                # Path should start AFTER this 5m bar
                entry_time_end = valid_long + pd.Timedelta(minutes=5)
            elif not pd.isna(valid_short):
                direction = 'short'
                entry_time = valid_short
                entry_price = resampled.loc[valid_short]['close']
                stop_price = orb_high
                entry_time_end = valid_short + pd.Timedelta(minutes=5)
                
            # Adjust entry_time for path slicing
            # For 1m close, entry is at 'entry_time' (the minute it closed). Path is subsequent minutes.
            # For 5m close, entry is at 'entry_time_end'.
            if trigger_type == '5m_close':
                entry_time = entry_time_end
            else:
                entry_time = entry_time + pd.Timedelta(minutes=1) # Start next minute
                
        # Get Price Path
        path = exec_data[exec_data.index >= entry_time].copy()
        if path.empty: continue
        
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
    # Optimize Points
    point_targets = np.arange(10, 105, 5)
    best_expectancy = -np.inf
    best_target = 0
    results = []
    
    for tgt in point_targets:
        wins = 0
        total_pnl = 0
        for t in trades:
            risk = abs(t['entry_price'] - t['stop_price']) # Risk depends on entry price vs orb side
            # Note: With close entry, risk >> orb_width potentially if candle was large.
            # Professional: Stop is typically ORB extreme.
            
            entry = t['entry_price']
            stop = t['stop_price']
            
            pnl = -risk
            
            path_h = t['path_highs']
            path_l = t['path_lows']
            
            for i in range(len(path_h)):
                h = path_h[i]
                l = path_l[i]
                
                hit_stop = False
                hit_target = False
                
                if t['direction'] == 'long':
                    if l <= stop: hit_stop = True
                    if h >= entry + tgt: hit_target = True
                else: # short
                    if h >= stop: hit_stop = True
                    if l <= entry - tgt: hit_target = True
                    
                if hit_stop and hit_target:
                    pnl = -risk
                    break
                elif hit_stop:
                    pnl = -risk
                    break
                elif hit_target:
                    pnl = tgt
                    wins+=1
                    break
            
            total_pnl += pnl
            
        n = len(trades)
        exp = total_pnl / n if n > 0 else 0
        results.append({'Target': tgt, 'Expectancy': exp, 'WinRate': (wins/n)*100})
        
    return pd.DataFrame(results)

def main():
    if not os.path.exists(DATA_FILE): return
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    
    # 1. Analyze 1m Close
    trades_1m = get_trades(df_active.copy(), '1m_close')
    if trades_1m:
        print(f"1m Close Trades found: {len(trades_1m)}")
        res_1m = optimize_targets(trades_1m)
        res_1m.to_csv(os.path.join(ARTIFACTS_DIR, 'close_res_1m.csv'), index=False)
        
    # 2. Analyze 5m Close
    trades_5m = get_trades(df_active.copy(), '5m_close')
    if trades_5m:
        print(f"5m Close Trades found: {len(trades_5m)}")
        res_5m = optimize_targets(trades_5m)
        res_5m.to_csv(os.path.join(ARTIFACTS_DIR, 'close_res_5m.csv'), index=False)
        
    # Generate Comparison Chart
    plt.figure(figsize=(10, 6))
    if trades_1m:
        plt.plot(res_1m['Target'], res_1m['Expectancy'], label='1m Close Entry', marker='o')
    if trades_5m:
        plt.plot(res_5m['Target'], res_5m['Expectancy'], label='5m Close Entry', marker='x')
        
    plt.title('Expectancy Comparison: 15m ORB Entry Triggers')
    plt.xlabel('Fixed Target (Points)')
    plt.ylabel('Expectancy (Points per Trade)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'compare_close_strategies.png'))
    plt.close()
    
    print("Comparison Complete.")

if __name__ == "__main__":
    main()
