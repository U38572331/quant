import databento as db
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import scipy.stats as stats
from statsmodels.graphics.tsaplots import plot_acf

# File paths
DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\nq_volatility\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\nq_volatility"

def main():
    print(f"Loading data from {DATA_PATH}...")
    try:
        # Load data
        df = db.read_dbn(DATA_PATH).to_df()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Prepare Daily Data
        # We use the date from index.
        # Note: Ideally we should handle trading sessions (e.g. 6pm-5pm), but using calendar date of the timestamp 
        # is standard for a quick approximation unless session handling is strictly required. 
        # Given the data length (15 years), this will be statistically robust.
        df['date'] = df.index.date
        
        # Aggregation
        daily_stats = df.groupby('date').agg({
            'high': 'max',
            'low': 'min'
        })
        
        # Calculate Range
        daily_stats['range_points'] = daily_stats['high'] - daily_stats['low']
        daily_stats['range_ticks'] = daily_stats['range_points'] / 0.25
        
        # Filter valid days
        daily_stats = daily_stats.dropna()
        daily_stats = daily_stats[daily_stats['range_ticks'] > 0]
        
        # Create DatetimeIndex for Time Series analysis
        daily_stats.index = pd.to_datetime(daily_stats.index)
        
        # --- Advanced Metrics ---
        # Rolling Metrics (20 days ~ 1 trading month)
        daily_stats['rolling_mean_20'] = daily_stats['range_ticks'].rolling(window=20).mean()
        daily_stats['rolling_std_20'] = daily_stats['range_ticks'].rolling(window=20).std()
        daily_stats['z_score'] = (daily_stats['range_ticks'] - daily_stats['rolling_mean_20']) / daily_stats['rolling_std_20']
        
        # Distribution Stats
        mean_vol = daily_stats['range_ticks'].mean()
        median_vol = daily_stats['range_ticks'].median()
        std_vol = daily_stats['range_ticks'].std()
        skewness = daily_stats['range_ticks'].skew()
        kurtosis = daily_stats['range_ticks'].kurt()
        
        percentiles = daily_stats['range_ticks'].quantile([0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
        
        print("\n=== Quant Metrics Report ===")
        print(f"Mean: {mean_vol:.2f} ticks")
        print(f"Median: {median_vol:.2f} ticks")
        print(f"Std Dev: {std_vol:.2f} ticks")
        print(f"Skewness: {skewness:.2f} (Positive = Fat Right Tail)")
        print(f"Kurtosis: {kurtosis:.2f} (High = Extreme Outliers)")
        print("\nPercentiles (Ticks):")
        print(percentiles)
        
        # --- Visualization ---
        plt.style.use('dark_background')
        # Set a nice color palette
        colors = sns.color_palette("viridis", as_cmap=False)
        
        # Figure 1: Timeseries & Regimes
        fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        
        # Rolling Volatility
        ax1.plot(daily_stats.index, daily_stats['range_ticks'], color='gray', alpha=0.5, label='Daily Range', linewidth=0.5)
        ax1.plot(daily_stats.index, daily_stats['rolling_mean_20'], color='#00ffcc', linewidth=1.5, label='20-Day Avg Range')
        ax1.fill_between(daily_stats.index, 
                         daily_stats['rolling_mean_20'] - daily_stats['rolling_std_20'],
                         daily_stats['rolling_mean_20'] + daily_stats['rolling_std_20'], 
                         color='#00ffcc', alpha=0.1, label='Volatility Bands (1 Std)')
        ax1.set_title('NQ Daily Range & Volatility Regime (20-Day Rolling)', fontsize=14, color='white')
        ax1.set_ylabel('Ticks', color='white')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.15)
        
        # Z-Score (Abnormality)
        # Color bars based on z-score magnitude
        z_colors = np.where(daily_stats['z_score'] > 2, '#ff4444', 
                   np.where(daily_stats['z_score'] < -2, '#44ff44', '#aaaaaa'))
        
        ax2.bar(daily_stats.index, daily_stats['z_score'], color=z_colors, width=1.0)
        ax2.axhline(2, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(-2, color='green', linestyle='--', alpha=0.5)
        ax2.set_title('Z-Score of Daily Volatility (Relative to 20-Day Avg)', fontsize=14, color='white')
        ax2.set_ylabel('Z-Score', color='white')
        ax2.grid(True, alpha=0.15)
        
        plt.tight_layout()
        save_path1 = os.path.join(OUTPUT_DIR, 'nq_vol_regime.png')
        plt.savefig(save_path1)
        print(f"Saved {save_path1}")
        
        # Figure 2: Statistical Distribution
        fig2 = plt.figure(figsize=(15, 10))
        gs = fig2.add_gridspec(2, 2)
        
        # Histogram & KDE
        ax_hist = fig2.add_subplot(gs[0, :])
        sns.histplot(daily_stats['range_ticks'], kde=True, ax=ax_hist, color='#cyan', stat='density')
        # Mark percentiles
        for p in [0.10, 0.50, 0.90, 0.99]:
            val = daily_stats['range_ticks'].quantile(p)
            ax_hist.axvline(val, color='yellow', linestyle=':', label=f'P{int(p*100)}: {val:.0f}')
        ax_hist.set_title(f'Distribution of Daily Range (Skew: {skewness:.2f}, Kurt: {kurtosis:.2f})', fontsize=14)
        ax_hist.legend()
        ax_hist.grid(True, alpha=0.15)
        
        # QQ Plot
        ax_qq = fig2.add_subplot(gs[1, 0])
        stats.probplot(daily_stats['range_ticks'], dist="norm", plot=ax_qq)
        ax_qq.get_lines()[0].set_color('#00ffcc') # Data points
        ax_qq.get_lines()[1].set_color('white')   # Line
        ax_qq.set_title('Q-Q Plot (Normality Check)', fontsize=14)
        ax_qq.grid(True, alpha=0.15)
        
        # Autocorrelation
        ax_acf = fig2.add_subplot(gs[1, 1])
        plot_acf(daily_stats['range_ticks'], ax=ax_acf, lags=40, color='white', vlines_kwargs={'colors': '#00ffcc'})
        ax_acf.set_title('Autocorrelation (Volatility Clustering)', fontsize=14)
        ax_acf.grid(True, alpha=0.15)
        
        plt.tight_layout()
        save_path2 = os.path.join(OUTPUT_DIR, 'nq_vol_stats.png')
        plt.savefig(save_path2)
        print(f"Saved {save_path2}")
        
        # Figure 3: Seasonality
        daily_stats['Year'] = daily_stats.index.year
        daily_stats['Month'] = daily_stats.index.month_name().str[:3] # Jan, Feb
        daily_stats['DayOfWeek'] = daily_stats.index.day_name().str[:3] # Mon, Tue
        
        # Order months and days properly
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        
        fig3, (ax_y, ax_m, ax_d) = plt.subplots(3, 1, figsize=(15, 12))
        
        sns.boxplot(data=daily_stats, x='Year', y='range_ticks', ax=ax_y, palette='viridis')
        ax_y.set_title('Volatility Distribution by Year', fontsize=12)
        ax_y.grid(True, alpha=0.1)
        
        sns.boxplot(data=daily_stats, x='Month', y='range_ticks', order=month_order, ax=ax_m, palette='cool')
        ax_m.set_title('Volatility Seasonality by Month', fontsize=12)
        ax_m.grid(True, alpha=0.1)
        
        valid_days = daily_stats[daily_stats['DayOfWeek'].isin(day_order)]
        sns.boxplot(data=valid_days, x='DayOfWeek', y='range_ticks', order=day_order, ax=ax_d, palette='cool')
        ax_d.set_title('Volatility Seasonality by Day of Week', fontsize=12)
        ax_d.grid(True, alpha=0.1)
        
        plt.tight_layout()
        save_path3 = os.path.join(OUTPUT_DIR, 'nq_vol_seasonality.png')
        plt.savefig(save_path3)
        print(f"Saved {save_path3}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
