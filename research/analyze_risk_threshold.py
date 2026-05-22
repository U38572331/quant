import pandas as pd
import numpy as np

df = pd.read_csv('trades_log.csv')
# Recalculate risk points more accurately
# If PnL > 0 (Win), risk was (PnL/20)/3. If PnL < 0 (Loss), risk was |PnL|/20.
df['Risk_Pts'] = np.where(df['PnL'] > 0, 
                        (df['PnL'] / 20.0) / 3.0, 
                        np.abs(df['PnL'] / 20.0))

results = []
# Test thresholds from 10 to 150 points
for threshold in range(10, 160, 10):
    filtered_df = df[df['Risk_Pts'] <= threshold]
    if len(filtered_df) == 0: continue
    
    total_trades = len(filtered_df)
    win_rate = (filtered_df['PnL'] > 0).mean()
    net_profit = filtered_df['PnL'].sum()
    expectancy = filtered_df['PnL'].mean()
    profit_factor = filtered_df[filtered_df['PnL'] > 0]['PnL'].sum() / np.abs(filtered_df[filtered_df['PnL'] <= 0]['PnL'].sum())
    
    results.append({
        'Max_Risk': threshold,
        'Trades': total_trades,
        'WinRate': win_rate,
        'NetProfit': net_profit,
        'Expectancy': expectancy,
        'ProfitFactor': profit_factor
    })

print(pd.DataFrame(results))
