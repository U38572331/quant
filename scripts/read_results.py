import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\backtest_results\ml_filter\ml_performance_compare.csv')
df['Threshold'] = df['Threshold'].fillna('Baseline')

print("=== All TP Sizes - Best Sharpe per TP ===")
for tp in sorted(df['TP_Size'].unique()):
    sub = df[df['TP_Size']==tp].sort_values('Sharpe', ascending=False)
    best = sub.iloc[0]
    base = sub[sub['Threshold']=='Baseline'].iloc[0]
    print(f"  TP={tp}: Baseline Sharpe={base['Sharpe']:.3f} PnL={base['TotalPnL']:.1f} | Best Threshold={best['Threshold']} Sharpe={best['Sharpe']:.3f} WR={best['WinRate']:.2%} PnL={best['TotalPnL']:.1f}")
