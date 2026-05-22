"""
Demo script to generate ATR and VWAP visualizations with sample data
"""
import pandas as pd
import numpy as np
import sys
sys.path.append(r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis')
from visualizer import PerformanceAnalyzer

# Create sample filtered results with ATR and VWAP metrics
np.random.seed(42)
n_strategies = 30

df_filtered = pd.DataFrame({
    'channel_period': np.random.choice([10, 15, 20, 30, 45, 60], n_strategies),
    'entry_type': np.random.choice(['touch', 'close'], n_strategies),
    'exit_type': np.random.choice(['fixed_points', 'r_multiple', 'trailing'], n_strategies),
    'stop_type': np.random.choice(['atr', 'fixed', 'swing'], n_strategies),
    'win_rate': np.random.uniform(60, 75, n_strategies),
    'total_trades': np.random.randint(100, 500, n_strategies),
    'sharpe_ratio': np.random.uniform(1.0, 3.0, n_strategies),
    'profit_factor': np.random.uniform(1.5, 3.5, n_strategies),
    'total_pnl': np.random.uniform(50000, 500000, n_strategies),
    'max_drawdown_pct': np.random.uniform(5, 25, n_strategies),
    'expectancy': np.random.uniform(100, 800, n_strategies),
    # ATR and VWAP metrics
    'avg_atr_at_entry': np.random.uniform(15, 35, n_strategies),
    'avg_vwap_distance': np.random.uniform(-10, 10, n_strategies),
    'pct_above_vwap': np.random.uniform(35, 65, n_strategies)
})

# Initialize analyzer
artifacts_dir = r'C:\Users\user\.gemini\antigravity\brain\2503dbf8-d983-437d-8e2f-a099c6fa0fcb'
analyzer = PerformanceAnalyzer(artifacts_dir)

# Generate ATR and VWAP visualizations
print("Generating ATR analysis visualization...")
analyzer.plot_atr_analysis(df_filtered)

print("Generating VWAP analysis visualization...")
analyzer.plot_vwap_analysis(df_filtered)

print("Generating combined ATR/VWAP visualization...")
analyzer.plot_atr_vwap_combined(df_filtered)

print("\nVisualizations generated successfully!")
print(f"Check {artifacts_dir} for PNG files")
