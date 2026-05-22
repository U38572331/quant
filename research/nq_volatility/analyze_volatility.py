import databento as db
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# File paths
DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\nq_volatility\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_IMG = r"C:\Users\user\.gemini\antigravity\scratch\nq_volatility\nq_volatility_chart.png"

def main():
    print(f"Loading data from {DATA_PATH}...")
    try:
        # Load data into DataFrame
        # The file is OHLCV-1m, so we expect columns like open, high, low, close, volume
        df = db.read_dbn(DATA_PATH).to_df()
        
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        print(f"Data loaded: {len(df)} 1-minute bars.")
        
        # Resample to Daily
        # Using 'D' might include weekends/holidays with NaN if we just resample, 
        # so we'll group by date to get actual trading days.
        # However, futures trade overnight. A "Trading Day" for NQ usually resets at 5pm or 6pm ET.
        # For simplicity in this context, unless specified, we'll use calendar day UTC/Local as per the data.
        # DBN data is typically UTC. We will use the date component of the UTC timestamp.
        
        # Create a date column
        df['date'] = df.index.date
        
        # Group by date to calculate Daily High and Low
        daily_stats = df.groupby('date').agg({
            'high': 'max',
            'low': 'min'
        })
        
        # Calculate Volatility
        daily_stats['range_points'] = daily_stats['high'] - daily_stats['low']
        daily_stats['range_ticks'] = daily_stats['range_points'] / 0.25
        
        # Remove any potential zero/NaN ranges if data is bad (though unlikely for 1m data unless missing)
        daily_stats = daily_stats.dropna()
        daily_stats = daily_stats[daily_stats['range_ticks'] > 0]
        
        # Statistics
        mean_vol = daily_stats['range_ticks'].mean()
        std_vol = daily_stats['range_ticks'].std()
        min_vol = daily_stats['range_ticks'].min()
        max_vol = daily_stats['range_ticks'].max()
        
        print("-" * 30)
        print(f"Analysis Period: {daily_stats.index[0]} to {daily_stats.index[-1]}")
        print(f"Total Trading Days: {len(daily_stats)}")
        print(f"Mean Daily Range: {mean_vol:.2f} ticks ({mean_vol*0.25:.2f} pts)")
        print(f"Std Dev Daily Range: {std_vol:.2f} ticks ({std_vol*0.25:.2f} pts)")
        print(f"Max Daily Range: {max_vol:.2f} ticks")
        print(f"Min Daily Range: {min_vol:.2f} ticks")
        print("-" * 30)
        
        # Plotting
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Time Series
        ax1.plot(daily_stats.index, daily_stats['range_ticks'], color='#00ffcc', linewidth=1, label='Daily Range')
        ax1.axhline(mean_vol, color='white', linestyle='--', label=f'Mean ({mean_vol:.0f})')
        ax1.set_title('NQ Daily Volatility (Ticks)', fontsize=14, color='white')
        ax1.set_ylabel('Ticks', color='white')
        ax1.legend()
        ax1.grid(True, alpha=0.2)
        
        # Plot 2: Histogram
        n, bins, patches = ax2.hist(daily_stats['range_ticks'], bins=100, color='#00aaff', alpha=0.7, edgecolor='black')
        ax2.axvline(mean_vol, color='white', linestyle='--', linewidth=2, label=f'Mean: {mean_vol:.0f}')
        ax2.axvline(mean_vol + std_vol, color='yellow', linestyle=':', linewidth=2, label=f'+1 Std: {mean_vol+std_vol:.0f}')
        ax2.axvline(mean_vol - std_vol, color='yellow', linestyle=':', linewidth=2, label=f'-1 Std: {mean_vol-std_vol:.0f}')
        ax2.set_title('Distribution of Daily Volatility', fontsize=14, color='white')
        ax2.set_xlabel('Ticks', color='white')
        ax2.set_ylabel('Frequency', color='white')
        ax2.legend()
        ax2.grid(True, alpha=0.2)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_IMG)
        print(f"Chart saved to {OUTPUT_IMG}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
