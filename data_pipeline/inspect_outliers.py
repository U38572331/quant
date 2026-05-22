import pandas as pd

try:
    df = pd.read_csv(r"C:\Users\user\.gemini\antigravity\scratch\backtest_trades.csv")
    print(f"Total Trades: {len(df)}")
    
    print("\n--- Top 5 Worst Losses ---")
    print(df.sort_values("PnL").head(5)[['Date', 'Type', 'Entry', 'Exit', 'PnL']])
    
    print("\n--- Top 5 Best Wins ---")
    print(df.sort_values("PnL", ascending=False).head(5)[['Date', 'Type', 'Entry', 'Exit', 'PnL']])
    
    print("\n--- Trades with Exit = EOD (Potential Force Close Issues) ---")
    eod = df[df['Result'] == 'EOD']
    print(f"Count: {len(eod)}")
    print(eod.sort_values("PnL").head(5)[['Date', 'Entry', 'Exit', 'PnL']])

except Exception as e:
    print(e)
