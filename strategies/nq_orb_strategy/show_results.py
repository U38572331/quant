import pandas as pd
import numpy as np

try:
    df = pd.read_csv('nq_orb_results.csv')
    print(f"Loaded {len(df)} trades.")
    
    scenarios = ['Result_1R', 'Result_1.5R', 'Result_2R']
    
    for scen in scenarios:
        if scen not in df.columns: continue
        
        print(f"\n--- {scen} ---")
        returns = df[scen]
        
        total_r = returns.sum()
        win_rate = (returns > 0).mean() * 100
        
        # Drawdown
        cum_ret = returns.cumsum()
        peak = cum_ret.cummax()
        dd = cum_ret - peak
        max_dd = dd.min()
        
        # Profit Factor
        gross_win = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        pf = gross_win / gross_loss if gross_loss != 0 else np.inf
        
        # Sharpe (Daily approximation)
        # We need dates for proper sharpe
        df['Date'] = pd.to_datetime(df['Date'])
        daily = df.groupby('Date')[scen].sum()
        params_sharpe = (daily.mean() / daily.std()) * (252**0.5) if daily.std() != 0 else 0
        
        print(f"Total Return: {total_r:.2f} R")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Profit Factor: {pf:.2f}")
        print(f"Max Drawdown: {max_dd:.2f} R")
        print(f"Sharpe Ratio: {params_sharpe:.2f}")

except Exception as e:
    print(f"Error: {e}")
