import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_pngs():
    file_path = r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\backtest_15m_orb_trades.csv"
    out_dir = r"C:\Users\user\.gemini\antigravity\brain\a5fd8b7e-ac0e-491e-952e-0df69a51156c"
    
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    df['Cumulative_PnL'] = df['PnL'].cumsum()
    df['HighWaterMark'] = df['Cumulative_PnL'].cummax()
    df['Drawdown'] = df['Cumulative_PnL'] - df['HighWaterMark']

    plt.style.use('dark_background')

    # 1. Equity Curve
    plt.figure(figsize=(10, 5))
    plt.plot(df['Date'], df['Cumulative_PnL'], color='#00ffcc', linewidth=2)
    plt.fill_between(df['Date'], df['Cumulative_PnL'], color='#00ffcc', alpha=0.1)
    plt.title('Cumulative PnL (Equity Curve)', fontsize=14)
    plt.ylabel('NQ Points')
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "equity_curve.png"), dpi=150)
    plt.close()

    # 2. Drawdown
    plt.figure(figsize=(10, 3))
    plt.plot(df['Date'], df['Drawdown'], color='#ff3366', linewidth=1)
    plt.fill_between(df['Date'], df['Drawdown'], color='#ff3366', alpha=0.3)
    plt.title('Drawdown (Points)', fontsize=14)
    plt.ylabel('NQ Points')
    plt.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "drawdown.png"), dpi=150)
    plt.close()

    # 3. Monthly Heatmap
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    monthly_pnl = df.groupby(['Year', 'Month'])['PnL'].sum().reset_index()
    monthly_pivot = monthly_pnl.pivot(index='Year', columns='Month', values='PnL').fillna(0)
    for m in range(1, 13):
        if m not in monthly_pivot.columns: monthly_pivot[m] = 0
    monthly_pivot = monthly_pivot[range(1, 13)]
    monthly_pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    plt.figure(figsize=(10, 4))
    sns.heatmap(monthly_pivot, annot=True, fmt=".0f", cmap='RdYlGn', center=0, cbar=False)
    plt.title('Monthly Returns Heatmap (Points)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "heatmap.png"), dpi=150)
    plt.close()
    
    print("PNG charts generated successfully.")

if __name__ == "__main__":
    generate_pngs()
