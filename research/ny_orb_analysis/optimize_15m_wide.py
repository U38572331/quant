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
        except: continue
            
        orb_data = day_df[(day_df.index >= orb_start) & (day_df.index < orb_end)]
        if orb_data.empty: continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_width = orb_high - orb_low
        if orb_width == 0: continue
            
        exec_data = day_df[(day_df.index >= orb_end) & (day_df.index <= session_end)]
        if exec_data.empty: continue
        
        entry_time = None
        direction = None
        entry_price = None
        
        if trigger_type == '1m_close':
            long_cond = exec_data['close'] > orb_high
            short_cond = exec_data['close'] < orb_low
            first_long = long_cond.idxmax() if long_cond.any() else pd.NaT
            first_short = short_cond.idxmax() if short_cond.any() else pd.NaT
            
            if pd.isna(first_long) and pd.isna(first_short): continue
            
            if not pd.isna(first_long) and (pd.isna(first_short) or first_long < first_short):
                direction = 'long'
                entry_time = first_long
                entry_price = exec_data.loc[first_long]['close']
            elif not pd.isna(first_short):
                direction = 'short'
                entry_time = first_short
                entry_price = exec_data.loc[first_short]['close']
                
            path_start = entry_time + pd.Timedelta(minutes=1)

        elif trigger_type == '5m_close':
            resampled = exec_data.resample('5min', closed='left', label='left').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            long_cond = resampled['close'] > orb_high
            short_cond = resampled['close'] < orb_low
            first_long = long_cond.idxmax() if long_cond.any() else pd.NaT
            first_short = short_cond.idxmax() if short_cond.any() else pd.NaT
            
            if pd.isna(first_long) and pd.isna(first_short): continue
            
            if not pd.isna(first_long) and (pd.isna(first_short) or first_long < first_short):
                direction = 'long'
                entry_time = first_long
                entry_price = resampled.loc[first_long]['close']
                path_start = first_long + pd.Timedelta(minutes=5)
            elif not pd.isna(first_short):
                direction = 'short'
                entry_time = first_short
                entry_price = resampled.loc[first_short]['close']
                path_start = first_short + pd.Timedelta(minutes=5)
        
        path = exec_data[exec_data.index >= path_start].copy()
        
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

def run_simulation(trades, points):
    wins = 0
    total_points = 0
    
    for t in trades:
        entry = t['entry_price']
        
        if t['direction'] == 'long':
            stop = t['orb_low']
            target = entry + points
        else: # short
            stop = t['orb_high']
            target = entry - points
            
        pnl = -(abs(entry - stop)) # Default Risk layout (Wide Stop)
        
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
                break # Loss
            elif hit_stop:
                break # Loss
            elif hit_target:
                pnl = points
                wins += 1
                break
        
        total_points += pnl
        
    n = len(trades)
    win_rate = (wins / n * 100) if n > 0 else 0
    expectancy = total_points / n if n > 0 else 0
    
    return {
        'Points': points,
        'WinRate': win_rate,
        'Expectancy': expectancy,
        'TotalPoints': total_points
    }

def main():
    if not os.path.exists(DATA_FILE): return
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    
    results = []
    
    # Analyze 1m Close
    trades_1m = get_trades(df_active.copy(), '1m_close')
    for pts in np.arange(10, 105, 5):
        results.append({**{'Trigger': '1m Close'}, **run_simulation(trades_1m, pts)})
        
    # Analyze 5m Close
    trades_5m = get_trades(df_active.copy(), '5m_close')
    for pts in np.arange(10, 105, 5):
        results.append({**{'Trigger': '5m Close'}, **run_simulation(trades_5m, pts)})
        
    res_df = pd.DataFrame(results)
    res_df.to_csv(os.path.join(ARTIFACTS_DIR, 'opt_15m_wide.csv'), index=False)
    
    print(res_df.sort_values(by='Expectancy', ascending=False).head(5))
    
    # Chart
    plt.figure(figsize=(10, 6))
    for trigger, grp in res_df.groupby('Trigger'):
        plt.plot(grp['Points'], grp['Expectancy'], marker='o', label=trigger)
    
    plt.axhline(0, color='black', linestyle='--')
    plt.title('15m ORB (Wide Stop): Fixed Points Expectancy')
    plt.xlabel('Target (Points)')
    plt.ylabel('Expectancy (Points per Trade)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'best_15m_wide.png'))
    plt.close()

if __name__ == "__main__":
    main()
