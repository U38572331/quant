import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob

# Configuration
DATA_FILE = r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv'
ARTIFACTS_DIR = r'C:\Users\user\.gemini\antigravity\brain\19288795-ea17-435e-a45c-dc9b64c40984'
ORB_START_TIME = '09:30'
ORB_END_TIME = '09:45' # Exclusive, so 15 mins: 30, 31, ... 44
SESSION_END_TIME = '16:00'

def load_and_prep_data(filepath):
    print("Loading data... (this may take a moment)")
    # Read CSV
    df = pd.read_csv(filepath)
    
    # Parse Dates
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    
    # Convert active timezone to US/Eastern
    # The data seems to be UTC (Z suffix). 
    df['dt_ny'] = df['ts_event'].dt.tz_convert('US/Eastern')
    
    return df

def select_active_contract(df):
    print("Selecting active contracts...")
    # Group by Date (NY) and Symbol to find max volume
    df['date_ny'] = df['dt_ny'].dt.date
    
    # Sum volume per symbol per day
    daily_vol = df.groupby(['date_ny', 'symbol'])['volume'].sum().reset_index()
    
    # Find symbol with max volume for each day
    max_vol_idx = daily_vol.groupby(['date_ny'])['volume'].idxmax()
    active_contracts = daily_vol.loc[max_vol_idx, ['date_ny', 'symbol']]
    
    # Merge back to filter original df
    # Rename for merge
    active_contracts.rename(columns={'symbol': 'active_symbol'}, inplace=True)
    
    df_merged = pd.merge(df, active_contracts, on='date_ny', how='left')
    
    # Filter where symbol matches active_symbol
    df_active = df_merged[df_merged['symbol'] == df_merged['active_symbol']].copy()
    
    return df_active

def analyze_orb(df):
    print("Analyzing ORB Strategy...")
    results = []
    
    # Set index and sort
    df.set_index('dt_ny', inplace=True)
    df.sort_index(inplace=True)
    
    # Group by Day (using date component of index)
    # Note: df.index.date returns numpy array of python dates
    # We can iterate unique dates, but slicing is still costly if not using index slice
    # Faster: groupby date
    
    # Extract date for grouping (preserving index)
    df['date_group'] = df.index.date
    grouped = df.groupby('date_group')
    
    for day, day_df in grouped:
        # Define Time Windows using the day object

        
        # Define Time Windows
        day_str = str(day)
        orb_start = pd.Timestamp(f"{day_str} {ORB_START_TIME}").tz_localize('US/Eastern')
        orb_end = pd.Timestamp(f"{day_str} {ORB_END_TIME}").tz_localize('US/Eastern')
        session_end = pd.Timestamp(f"{day_str} {SESSION_END_TIME}").tz_localize('US/Eastern')
        
        # Get ORB Data
        orb_data = day_df[(day_df.index >= orb_start) & (day_df.index < orb_end)]
        
        if orb_data.empty:
            continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_width = orb_high - orb_low
        
        if orb_width == 0:
            continue
            
        # Get Post-ORB Data (Execution Phase)
        exec_data = day_df[(day_df.index >= orb_end) & (day_df.index <= session_end)]
        
        if exec_data.empty:
            continue
            
        # Determine Breakout
        # Find first candle that breaks ORB High or High
        # We simplify: Check open/high/low/close of 1m bars
        
        # Determine Breakout (Vectorized)
        # Find first index where condition is met
        long_breakouts = exec_data[exec_data['high'] > orb_high]
        short_breakouts = exec_data[exec_data['low'] < orb_low]
        
        first_long = long_breakouts.index[0] if not long_breakouts.empty else pd.NaT
        first_short = short_breakouts.index[0] if not short_breakouts.empty else pd.NaT
        
        if pd.isna(first_long) and pd.isna(first_short):
            # No breakout
            results.append({
                'date': day,
                'orb_width': orb_width,
                'breakout': 'none',
                'mfe_r': 0,
                'hit_stop': False
            })
            continue
            
        # Compare timestamps to see which happened first
        if not pd.isna(first_long) and (pd.isna(first_short) or first_long < first_short):
            breakout_dir = 'long'
            entry_price = orb_high
            entry_time = first_long
            stop_price = orb_low
        else:
            breakout_dir = 'short'
            entry_price = orb_low
            entry_time = first_short
            stop_price = orb_high
                
        # Analyze Outcome (Vectorized)
        post_entry = exec_data[exec_data.index > entry_time]
        
        if post_entry.empty:
             results.append({
                'date': day,
                'orb_width': orb_width,
                'breakout': 'none', # Treated as none/scratch
                'mfe_r': 0,
                'hit_stop': False
            })
             continue
             
        if breakout_dir == 'long':
            mae_price = post_entry['low'].min()
            mfe_price = post_entry['high'].max()
            
            max_pnl = mfe_price - entry_price
            hit_stop = mae_price <= stop_price
            
        else: # Short
            mae_price = post_entry['high'].max()
            mfe_price = post_entry['low'].min()
            
            max_pnl = entry_price - mfe_price
            hit_stop = mae_price >= stop_price
            
        mfe_r = max_pnl / orb_width
        
        results.append({
            'date': day,
            'orb_width': orb_width,
            'breakout': breakout_dir,
            'mfe_r': mfe_r,
            'hit_stop': hit_stop
        })
        
    return pd.DataFrame(results)

def generate_charts(res_df):
    print("Generating Charts...")
    if res_df.empty:
        print("No results to plot.")
        return

    # Filter out 'none' breakouts
    df_trades = res_df[res_df['breakout'] != 'none'].copy()
    
    # 1. ORB Width vs MFE (Scatter)
    plt.figure(figsize=(10, 6))
    plt.scatter(df_trades['orb_width'], df_trades['mfe_r'] * df_trades['orb_width'], alpha=0.5)
    plt.title('Opening Volatility (Points) vs Subsequent Move (Points)')
    plt.xlabel('ORB Width (Points)')
    plt.ylabel('Max Favorable Excursion (Points)')
    plt.grid(True)
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'volatility_scatter.png'))
    plt.close()
    
    # 2. Daily Range Distribution (Histogram of ORB Width)
    plt.figure(figsize=(10, 6))
    plt.hist(df_trades['orb_width'], bins=30, color='skyblue', edgecolor='black')
    plt.title('Distribution of 15m ORB Width')
    plt.xlabel('Points')
    plt.ylabel('Frequency')
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'orb_width_dist.png'))
    plt.close()

    # 3. Win Rate Estimate (very rough, assuming we hold for max day move, checking if MFE > X R)
    # This is "Potential" win rate (did price reach X R at any point?)
    r_levels = [1, 2, 3, 4, 5]
    win_rates = []
    
    for r in r_levels:
        # Win if MFE >= R * Width. (Ignoring stop hit timing for this High Level stat, assume active trail or broad stop)
        wins = df_trades[df_trades['mfe_r'] >= r]
        rate = len(wins) / len(df_trades) * 100
        win_rates.append(rate)
        
    plt.figure(figsize=(8, 5))
    plt.bar([f"{r}R" for r in r_levels], win_rates, color='green')
    plt.title('Probability of Reaching Target R-Multiple (Session MFE)')
    plt.xlabel('Target')
    plt.ylabel('Frequency (%)')
    plt.grid(axis='y')
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'win_probability.png'))
    plt.close()
    
    print(f"Charts saved to {ARTIFACTS_DIR}")

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: Data file not found at {DATA_FILE}")
        return
        
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    results = analyze_orb(df_active)
    
    print(results.describe())
    
    generate_charts(results)
    
    # Save CSV Results
    results.to_csv(os.path.join(ARTIFACTS_DIR, 'orb_results.csv'), index=False)
    print("Analysis Complete.")

if __name__ == "__main__":
    main()
