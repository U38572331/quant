
import pandas as pd
import numpy as np
import os

# Settings
FILE_PATH = r"C:\Users\user\Desktop\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
OUTPUT_PATH = "features.csv"
RTH_START = "09:30"
RTH_END = "16:15"
ORB_END = "09:45"
TICK_SIZE = 0.25 # NQ/ES tick size usually
VA_PCT = 0.70

def calculate_vp(df_day):
    """
    Calculate Volume Profile metrics for a single day dataframe (RTH only).
    Returns: POC, VAH, VAL
    """
    if df_day.empty:
        return np.nan, np.nan, np.nan
    

    # Create price bins
    prices = df_day['close'].values 
    volumes = df_day['volume'].values
    
    # Use integer keys for precision
    price_vol = {}
    for p, v in zip(prices, volumes):
        # Key is number of ticks
        k = int(round(p / TICK_SIZE))
        price_vol[k] = price_vol.get(k, 0) + v
        
    if not price_vol:
         return np.nan, np.nan, np.nan

    sorted_keys = sorted(price_vol.keys())
    total_volume = sum(price_vol.values())
    
    # 1. POC
    max_vol = -1
    poc_key = sorted_keys[0]
    for k in sorted_keys:
        if price_vol[k] > max_vol:
            max_vol = price_vol[k]
            poc_key = k
            
    poc_price = poc_key * TICK_SIZE
            
    # 2. Value Area
    current_vol = max_vol
    target_vol = total_volume * VA_PCT
    
    idx_poc = sorted_keys.index(poc_key)
    idx_up = idx_poc
    idx_down = idx_poc
    
    while current_vol < target_vol:
        vol_up = 0
        vol_down = 0
        
        can_go_up = idx_up < len(sorted_keys) - 1
        can_go_down = idx_down > 0
        
        if not can_go_up and not can_go_down:
            break
            
        if can_go_up:
            vol_up = price_vol[sorted_keys[idx_up + 1]]
        if can_go_down:
            vol_down = price_vol[sorted_keys[idx_down - 1]]
            
        if vol_up > vol_down:
             idx_up += 1
             current_vol += vol_up
        elif vol_down > vol_up:
             idx_down -= 1
             current_vol += vol_down
        else: 
             if can_go_up:
                 idx_up += 1
                 current_vol += vol_up
             if can_go_down:
                 idx_down -= 1
                 current_vol += vol_down
                 
    return poc_price, sorted_keys[idx_up] * TICK_SIZE, sorted_keys[idx_down] * TICK_SIZE

def main():
    print("Loading data...")
    df = pd.read_csv(FILE_PATH, usecols=['ts_event', 'open', 'high', 'low', 'close', 'volume'])
    
    print("Preprocessing...")
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    
    df = df.set_index('ts_event')
    if df.index.tz is None:
         df = df.tz_localize('UTC')
    df = df.tz_convert('US/Eastern')
    
    df = df.sort_index()
    df = df[~df.index.duplicated(keep='last')]
    
    # Pre-calculate masks to speed up
    # We can rely on index properties
    
    features_list = []
    history_metrics = {}
    
    print("Grouping by day...")
    # Group by date using simple string or date object
    grouped = df.groupby(df.index.date)
    
    # Get all days sorted
    all_days = sorted(list(grouped.groups.keys()))
    
    print(f"Processing {len(all_days)} days...")
    
    for i, day in enumerate(all_days):
        if i % 100 == 0:
            print(f"Day {i}/{len(all_days)}")
            
        day_data = grouped.get_group(day)
        
        # Define Time Masks
        rth_mask = day_data.between_time(RTH_START, RTH_END)
        orb_mask = day_data.between_time(RTH_START, ORB_END)
        
        if rth_mask.empty or orb_mask.empty:
            if i < 5:
                print(f"Day {day} skipped. Data range: {day_data.index[0]} to {day_data.index[-1]}")
                print(f"RTH mask len: {len(rth_mask)}, ORB mask len: {len(orb_mask)}")
            continue

            
        # --- Current Day Features ---
        orb_high = orb_mask['high'].max()
        orb_low = orb_mask['low'].min()
        orb_vol = orb_mask['volume'].sum()
        orb_open = orb_mask['open'].iloc[0]
        orb_close = orb_mask['close'].iloc[-1]
        orb_direction = 1 if orb_close > orb_open else 0
        
        # --- Target ---
        rth_open = rth_mask['open'].iloc[0]
        rth_close = rth_mask['close'].iloc[-1]
        daily_bias = 1 if rth_close > rth_open else 0
        
        # --- History Stats ---
        poc, vah, val = calculate_vp(rth_mask)
        history_metrics[day] = {
            'poc': poc, 'vah': vah, 'val': val, 'vol': rth_mask['volume'].sum()
        }
        
        feature_row = {
            'date': day,
            'orb_range': orb_high - orb_low,
            'orb_vol': orb_vol,
            'orb_dir': orb_direction,
            'target_bias': daily_bias,
            'rth_open': rth_open,
            'rth_close': rth_close
        }
        
        
        # Robust History Lookup
        # Get last 5 available days strictly BEFORE today
        valid_days = sorted([d for d in history_metrics.keys() if d < day])
        available_history = valid_days[-5:]
        
        if len(available_history) < 5:
            # Not enough history
            pass
        else:
             # Check if the most recent history is actually recent? 
             # (Optional: e.g. don't use history from a year ago)
             # For now, just take last 5 valid sessions
             
             for lag_idx, hist_day in enumerate(reversed(available_history)):
                 # lag_idx 0 -> most recent (Lag 1)
                 lag = lag_idx + 1
                 stats = history_metrics[hist_day]
                 
                 feature_row[f'lag{lag}_poc'] = stats['poc']
                 feature_row[f'lag{lag}_vah'] = stats['vah']
                 feature_row[f'lag{lag}_val'] = stats['val']
                 feature_row[f'lag{lag}_vol'] = stats['vol']
                 
                 feature_row[f'open_vs_lag{lag}_val'] = 1 if orb_open > stats['vah'] else (-1 if orb_open < stats['val'] else 0)
                 feature_row[f'd_open_lag{lag}_poc'] = rth_open - stats['poc']
             
             features_list.append(feature_row)
        
        # Save current day stats for FUTURE days
        # Only if we successfully calculated targets/features for this day?
        # Actually we computed VP, so we save it regardless of whether we could make a prediction (history) for today.
        # But wait, we already saved it above.

            
    features_df = pd.DataFrame(features_list)
    features_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(features_df)} samples to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
