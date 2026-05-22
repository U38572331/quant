import pandas as pd
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\backtest_15m_orb_trades.csv')
print(f"Total Trades: {len(df)}")
print("Results:", df.groupby('Result').size().to_dict())
print(f"Total PnL: {df['PnL'].sum():.2f}")
print(f"Avg PnL: {df['PnL'].mean():.2f}")
if len(df) > 0:
    wins = len(df[df['Result'] == 'Win'])
    print(f"Win Rate: {wins/len(df):.2%}")
print("\nFirst 5 trades:")
print(df.head())
