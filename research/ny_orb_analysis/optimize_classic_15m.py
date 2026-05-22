import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Configuration
DATA_FILE = r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv'
ARTIFACTS_DIR = r'C:\Users\user\.gemini\antigravity\brain\19288795-ea17-435e-a45c-dc9b64c40984'

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

def get_trades(df):
    print(f"Identifying Trades (Instant Entry)...")
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
        except: continue
        
        # Determine 15m ORB range
        orb_data = day_df[(day_df.index >= orb_start) & (day_df.index < orb_end)]
        if orb_data.empty: continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_width = orb_high - orb_low
        if orb_width == 0: continue
            
        exec_data = day_df[(day_df.index >= orb_end) & (day_df.index <= session_end)]
        if exec_data.empty: continue
        
        # Instant Breakout Logic
        long_breakouts = exec_data[exec_data['high'] > orb_high]
        short_breakouts = exec_data[exec_data['low'] < orb_low]
        
        first_long = long_breakouts.index[0] if not long_breakouts.empty else pd.NaT
        first_short = short_breakouts.index[0] if not short_breakouts.empty else pd.NaT
        
        entry_time = None
        direction = None
        entry_price = None
        
        if pd.isna(first_long) and pd.isna(first_short): continue
        
        if not pd.isna(first_long) and (pd.isna(first_short) or first_long < first_short):
            direction = 'long'
            entry_time = first_long
            entry_price = orb_high + 0.25 # Tick above
        else:
            direction = 'short'
            entry_time = first_short
            entry_price = orb_low - 0.25
        
        # Get path
        path = exec_data[exec_data.index >= entry_time].copy()
        
        trades.append({
            'date': day,
            'direction': direction,
            'entry_price': entry_price,
            'orb_high': orb_high,
            'orb_low': orb_low,
            'path_highs': path['high'].values,
            'path_lows': path['low'].values
        })
        
    return trades

def run_simulation(trades, target_val, mode='points'):
    wins = 0
    total_points = 0
    
    for t in trades:
        entry = t['entry_price']
        
        if t['direction'] == 'long':
            stop = t['orb_low']
            if mode == 'points':
                target = entry + target_val
            else: # R
                risk = entry - stop
                target = entry + (risk * target_val)
        else:
            stop = t['orb_high']
            if mode == 'points':
                target = entry - target_val
            else:
                risk = stop - entry
                target = entry - (risk * target_val)
                
        pnl = -(abs(entry - stop)) # Default risk (loss)
        
        path_h = t['path_highs']
        path_l = t['path_lows']
        
        for i in range(len(path_h)):
            h = path_h[i]
            l = path_l[i]
            
            hit_stop = False
            hit_target = False
            
            if t['direction'] == 'long':
                if l <= stop: hit_stop = True
                if h >= target: hit_target = True
            else:
                if h >= stop: hit_stop = True
                if l <= target: hit_target = True
                
            if hit_stop and hit_target:
                pnl = -(abs(entry - stop))
                break
            elif hit_stop:
                pnl = -(abs(entry - stop))
                break
            elif hit_target:
                if mode == 'points':
                    pnl = target_val
                else:
                    risk = abs(entry - stop)
                    pnl = risk * target_val
                wins += 1
                break
        
        total_points += pnl
        
    n = len(trades)
    win_rate = (wins / n * 100) if n > 0 else 0
    expectancy = total_points / n if n > 0 else 0
    
    return {
        'Target': target_val,
        'Type': mode,
        'WinRate': win_rate,
        'Expectancy': expectancy,
        'TotalPoints': total_points
    }

def main():
    if not os.path.exists(DATA_FILE): return
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    
    trades = get_trades(df_active)
    results = []
    
    # Sweep Fixed Points
    for pts in np.arange(10, 105, 5):
        results.append(run_simulation(trades, pts, 'points'))
        
    # Sweep R
    for r in [0.5, 1, 1.5, 2, 2.5, 3]:
        results.append(run_simulation(trades, r, 'R'))
        
    res_df = pd.DataFrame(results)
    res_df.to_csv(os.path.join(ARTIFACTS_DIR, 'opt_classic_15m.csv'), index=False)
    
    print("\n--- Top Results (Instant Entry + ORB Stop) ---")
    print(res_df.sort_values(by='Expectancy', ascending=False).head(10))

if __name__ == "__main__":
    main()
