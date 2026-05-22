import pandas as pd
import numpy as np

OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\results"
CSV_PATH = f"{OUTPUT_DIR}/opt_trades.csv"

def analyze():
    print("Loading trade results...")
    try:
        df = pd.read_csv(CSV_PATH)
    except:
        print("Could not load trades csv.")
        return

    # Metrics
    # We want to find the best SL/TP Combo
    
    # 1. Overall Stats per Config
    stats = df.groupby(['SL_Type', 'TP_R']).agg(
        Total_PnL=('PnL', 'sum'),
        Count=('PnL', 'count'),
        Win_Rate=('Result', lambda x: (x=='TP').mean()), # Approximate WinRate (TP vs SL/EOD)
        # Note: WinRate is PnL > 0 usually
        Real_Win_Rate=('PnL', lambda x: (x>0).mean()),
        Avg_Trade=('PnL', 'mean'),
        Std_Trade=('PnL', 'std')
    ).reset_index()
    
    stats['Sharpe'] = stats['Avg_Trade'] / stats['Std_Trade'] * np.sqrt(252*4) # Rough annualization assuming 4 trades/day
    
    print("\nTop 5 Configurations by Total PnL:")
    top_pnl = stats.sort_values('Total_PnL', ascending=False).head(5)
    print(top_pnl.to_string(index=False))
    
    print("\nTop 5 Configurations by Sharpe Ratio:")
    top_sharpe = stats.sort_values('Sharpe', ascending=False).head(5)
    print(top_sharpe.to_string(index=False))
    
    # Check Best Config details
    best = top_pnl.iloc[0]
    print(f"\nBest Config: SL={best['SL_Type']}, TP={best['TP_R']}")
    
    # Check ML feature importance consistency (if we ran it again, but here we just read stats)
    # We can infer value from 'Real_Win_Rate'.
    
if __name__ == "__main__":
    analyze()
