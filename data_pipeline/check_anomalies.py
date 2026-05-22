import pandas as pd

try:
    df = pd.read_csv(r"C:\Users\user\backtest_trades.csv")
    
    # Filter anomalies
    large_loss = df[df['PnL'] < -400]
    large_win = df[df['PnL'] > 800]
    bad_prices = df[(df['Entry'] < 1000) | (df['Entry'] > 40000) | (df['Exit'] < 1000) | (df['Exit'] > 40000)]
    
    print(f"--- Large Losses (< -400) : {len(large_loss)} ---")
    if not large_loss.empty:
        print(large_loss.sort_values("PnL").head(10)[['Date', 'Type', 'Entry', 'Exit', 'PnL', 'Result']])
        
    print(f"\n--- Large Wins (> 800) : {len(large_win)} ---")
    if not large_win.empty:
        print(large_win.sort_values("PnL", ascending=False).head(10)[['Date', 'Type', 'Entry', 'Exit', 'PnL']])

    print(f"\n--- Bad Prices (<1k or >40k) : {len(bad_prices)} ---")
    if not bad_prices.empty:
        print(bad_prices.head(10)[['Date', 'Entry', 'Exit']])

except Exception as e:
    print(e)
