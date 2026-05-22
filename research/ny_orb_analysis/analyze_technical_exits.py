
import pandas as pd

def analyze_tech_exits():
    df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\brain\2503dbf8-d983-437d-8e2f-a099c6fa0fcb\donchian_results_all.csv')
    
    # Filter for technical exits (ATR-based or Trailing)
    # User wants "Donchian or ATR". ATR Stop is the closest to ATR exit if using R-Multiple.
    # Also include ExitType.TRAILING.
    
    # Condition: (StopType == ATR) OR (ExitType == TRAILING)
    # AND ExitType != TIME_BASED
    
    mask = (df['exit_type'] != 'time_based') & (
        (df['stop_type'] == 'atr') | (df['exit_type'] == 'trailing')
    )
    df_tech = df[mask]
    
    # Filter for reasonable trade count
    df_tech = df_tech[df_tech['total_trades'] > 1500]
    
    # Sort by Sharpe and Profit Factor
    top_sharpe = df_tech.sort_values('sharpe_ratio', ascending=False).head(5)
    
    print("Top ATR/Trailing Strategies:")
    cols = ['channel_period', 'entry_type', 'exit_type', 'exit_param', 'stop_type', 'stop_param', 'total_trades', 'win_rate', 'sharpe_ratio', 'profit_factor', 'recovery_factor', 'max_drawdown_pct']
    print(top_sharpe[cols])
    
    top_sharpe[cols].to_csv('best_atr_strategies.csv', index=False)

if __name__ == "__main__":
    analyze_tech_exits()
