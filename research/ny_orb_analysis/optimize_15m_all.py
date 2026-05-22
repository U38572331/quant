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
        except: continue
            
        orb_data = day_df[(day_df.index >= orb_start) & (day_df.index < orb_end)]
        if orb_data.empty: continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_width = orb_high - orb_low
        if orb_width == 0: continue
            
        exec_data = day_df[(day_df.index >= orb_end) & (day_df.index <= session_end)]
        if exec_data.empty: continue
        
        # Trigger Logic & Candle Stats
        candle_low = None
        candle_high = None
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
                candle_low = exec_data.loc[first_long]['low'] # Low of breakout candle
            elif not pd.isna(first_short):
                direction = 'short'
                entry_time = first_short
                entry_price = exec_data.loc[first_short]['close']
                candle_high = exec_data.loc[first_short]['high'] # High of breakout candle
                
            path_start = entry_time + pd.Timedelta(minutes=1)

        elif trigger_type == '5m_close':
            # Resample 5m
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
                candle_low = resampled.loc[first_long]['low']
                path_start = first_long + pd.Timedelta(minutes=5)
            elif not pd.isna(first_short):
                direction = 'short'
                entry_time = first_short
                entry_price = resampled.loc[first_short]['close']
                candle_high = resampled.loc[first_short]['high']
                path_start = first_short + pd.Timedelta(minutes=5)
        
        # Get Path
        path = exec_data[exec_data.index >= path_start].copy()
        
        trades.append({
            'date': day,
            'direction': direction,
            'entry_price': entry_price,
            'orb_high': orb_high,
            'orb_low': orb_low,
            'candle_low': candle_low,
            'candle_high': candle_high,
            'path_highs': path['high'].values,
            'path_lows': path['low'].values
        })
        
    return trades

def run_simulation(trades, stop_mode='orb_extreme', target_r=2.0):
    # stop_mode: 'orb_extreme' or 'candle_extreme'
    wins = 0
    total_r = 0
    
    for t in trades:
        entry = t['entry_price']
        
        # Determine Stop Price
        if t['direction'] == 'long':
            if stop_mode == 'orb_extreme':
                stop = t['orb_low']
            else: # candle_extreme
                stop = t['candle_low']
                # Check for invalid stop (entry <= stop)
                if stop >= entry: stop = t['orb_low'] # Fallback
                
            risk = entry - stop
            target = entry + (risk * target_r)
            
        else: # short
            if stop_mode == 'orb_extreme':
                stop = t['orb_high']
            else:
                stop = t['candle_high']
                if stop <= entry: stop = t['orb_high'] # Fallback
            
            risk = stop - entry
            target = entry - (risk * target_r)
            
        # Simulate
        pnl_r = -1.0 # Default loss
        
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
                pnl_r = -1.0
                break
            elif hit_stop:
                pnl_r = -1.0
                break
            elif hit_target:
                pnl_r = target_r
                wins += 1
                break
        
        total_r += pnl_r
        
    n = len(trades)
    win_rate = (wins / n * 100) if n > 0 else 0
    expectancy = total_r / n if n > 0 else 0
    
    return {
        'StopMode': stop_mode,
        'TargetR': target_r,
        'WinRate': win_rate,
        'Expectancy': expectancy,
        'TotalR': total_r,
        'NumTrades': n
    }

def main():
    if not os.path.exists(DATA_FILE): return
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    
    results = []
    
    # 1. 1m Close Analysis
    trades_1m = get_trades(df_active.copy(), '1m_close')
    print(f"1m Trades: {len(trades_1m)}")
    
    for r in [1, 1.5, 2, 2.5, 3, 4, 5]:
        results.append({**{'Trigger': '1m Close'}, **run_simulation(trades_1m, 'orb_extreme', r)})
        results.append({**{'Trigger': '1m Close'}, **run_simulation(trades_1m, 'candle_extreme', r)})
        
    # 2. 5m Close Analysis
    trades_5m = get_trades(df_active.copy(), '5m_close')
    print(f"5m Trades: {len(trades_5m)}")
    
    for r in [1, 1.5, 2, 2.5, 3, 4, 5]:
        results.append({**{'Trigger': '5m Close'}, **run_simulation(trades_5m, 'orb_extreme', r)})
        results.append({**{'Trigger': '5m Close'}, **run_simulation(trades_5m, 'candle_extreme', r)})
        
    res_df = pd.DataFrame(results)
    print("\n--- Optimization Results (Sorted by Expectancy) ---")
    print(res_df.sort_values(by='Expectancy', ascending=False))
    
    res_df.to_csv(os.path.join(ARTIFACTS_DIR, 'opt_15m_all.csv'), index=False)
    
    # Charting
    # Filter for Candle Extreme (Tight Stop) as standard failed
    df_tight = res_df[res_df['StopMode'] == 'candle_extreme']
    
    plt.figure(figsize=(10, 6))
    for trigger, grp in df_tight.groupby('Trigger'):
        plt.plot(grp['TargetR'], grp['Expectancy'], marker='o', label=f"{trigger} (Tight Stop)")
        
    plt.axhline(0, color='black', linestyle='--', linewidth=1)
    plt.title('15m ORB: Tight Stop (Candle Low) Performance')
    plt.xlabel('Target (R-Multiple)')
    plt.ylabel('Expectancy (R per Trade)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'best_15m_config.png'))
    plt.close()

if __name__ == "__main__":
    main()
