
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def plot_equity():
    try:
        df = pd.read_csv("src/equity_curve.csv", parse_dates=['timestamp'], index_col='timestamp')
    except:
        # Try finding the date column if index is not named timestamp
        df = pd.read_csv("src/equity_curve.csv", index_col=0, parse_dates=True)
        
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['Cumulative_PnL'], label='Strategy Equity', color='blue', linewidth=2)
    
    plt.title('ML ORB Strategy - Cumulative PnL (Test Set)', fontsize=14)
    plt.xlabel('Date')
    plt.ylabel('Points (NQ)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Format Date
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig("src/equity_curve.png")
    print("Chart saved to src/equity_curve.png")

if __name__ == "__main__":
    plot_equity()
