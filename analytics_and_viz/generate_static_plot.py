import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_static_plot():
    df = pd.read_csv("backtest_trades.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['CumPnL'] = df['PnL'].cumsum()

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(20, 10), dpi=150)
    
    ax.plot(df['Date'], df['CumPnL'], color='#00ff88', linewidth=2.5, label='Cumulative PnL')
    ax.fill_between(df['Date'], df['CumPnL'], color='#00ff88', alpha=0.1)
    
    ax.set_title('NQ ORB + VWAP Strategy Equity Curve (2021-2025)', fontsize=18, color='#00ff88', pad=20)
    ax.set_ylabel('Points', fontsize=12)
    ax.grid(True, which='both', color='#333', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    output_path = r"C:\Users\user\.gemini\antigravity\brain\c31344a2-fc59-4a9d-bc24-28645bf47868\equity_static_highres.png"
    plt.savefig(output_path)
    print(f"Static Plot Generated: {output_path}")

if __name__ == "__main__":
    generate_static_plot()
