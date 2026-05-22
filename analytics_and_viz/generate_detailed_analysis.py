import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load trades
trades_file = r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_30m_fixed.csv'
df = pd.read_csv(trades_file)

# Convert to datetime handling offsets
df['exit_time'] = pd.to_datetime(df['exit_time'], utc=True).dt.tz_convert('America/New_York')
df['date'] = df['exit_time'].dt.date
df['month'] = df['exit_time'].dt.month
df['year'] = df['exit_time'].dt.year

# 1. Equity and Drawdown
df['cum_pnl'] = df['pnl'].cumsum()
df['peak'] = df['cum_pnl'].cummax()
df['drawdown'] = df['cum_pnl'] - df['peak']

plt.figure(figsize=(15, 10))

# Subplot 1: Equity Curve
plt.subplot(2, 1, 1)
plt.plot(df['exit_time'], df['cum_pnl'], label='Cumulative PnL (Points)', color='blue')
plt.title('NQ 30m ORB Cumulative PnL', fontsize=14)
plt.ylabel('Points')
plt.grid(True, alpha=0.3)
plt.legend()

# Subplot 2: Drawdown
plt.subplot(2, 1, 2)
plt.fill_between(df['exit_time'], df['drawdown'], 0, color='red', alpha=0.3, label='Drawdown')
plt.title('Strategy Drawdown (Points)', fontsize=14)
plt.ylabel('Points')
plt.grid(True, alpha=0.3)
plt.legend()

plt.tight_layout()
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_detailed_equity_dd.png')

# 2. Monthly Returns Heatmap
monthly_pnl = df.groupby(['year', 'month'])['pnl'].sum().unstack()
plt.figure(figsize=(12, 8))
sns.heatmap(monthly_pnl, annot=True, fmt=".0f", cmap='RdYlGn', center=0)
plt.title('Monthly PnL Heatmap (Points)', fontsize=14)
plt.xlabel('Month')
plt.ylabel('Year')
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_monthly_heatmap.png')

# 3. Trade Distribution
plt.figure(figsize=(10, 6))
sns.histplot(df['pnl'], bins=50, kde=True, color='purple')
plt.axvline(0, color='black', linestyle='--')
plt.title('Distribution of Trade PnL (Points)', fontsize=14)
plt.xlabel('PnL Points')
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_pnl_dist.png')

# 4. Performance by Trade Type (Long vs Short)
# Fixed groupby apply
def get_win_rate(x):
    return (x['pnl'] > 0).mean() * 100

type_stats = df.groupby('type')['pnl'].agg(['count', 'sum', 'mean']).reset_index()
wr_series = df.groupby('type').apply(get_win_rate, include_groups=False)
type_stats['win_rate'] = type_stats['type'].map(wr_series)

print("\n--- Performance by Type ---")
print(type_stats)

plt.figure(figsize=(8, 5))
sns.barplot(data=type_stats, x='type', y='sum', palette='viridis')
plt.title('Total PnL by Trade Type (Long vs Short)', fontsize=14)
plt.ylabel('Total Points')
plt.savefig(r'C:\Users\user\.gemini\antigravity\scratch\nq_type_performance.png')

print("\nDetailed analysis charts generated.")
