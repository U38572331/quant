"""
Main execution script for Donchian Breakout optimization
Orchestrates data loading, parameter sweep, filtering, and reporting
"""

import pandas as pd
import numpy as np
import argparse
import os
import sys
from datetime import datetime

from ml_optimizer import MLOptimizer
from visualizer import PerformanceAnalyzer


# Configuration
DATA_FILE = r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv'
ARTIFACTS_DIR = r'C:\Users\user\.gemini\antigravity\brain\2503dbf8-d983-437d-8e2f-a099c6fa0fcb'

# RTH Settings (Regular Trading Hours)
SESSION_START = '09:30'
SESSION_END = '16:00'


def load_and_prep_data(filepath: str) -> pd.DataFrame:
    """Load and prepare 1-minute OHLCV data"""
    print("="*80)
    print("LOADING AND PREPARING DATA")
    print("="*80)
    print(f"Data file: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df):,} rows")
    
    # Parse timestamp
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df['dt_ny'] = df['ts_event'].dt.tz_convert('US/Eastern')
    
    # Extract OHLCV columns (assuming standard names)
    # Columns: ts_event, open, high, low, close, volume, symbol
    print(f"Columns: {df.columns.tolist()}")
    
    return df


def select_active_contract(df: pd.DataFrame) -> pd.DataFrame:
    """Select most active contract for each day"""
    print("\nSelecting active contracts by volume...")
    
    df['date_ny'] = df['dt_ny'].dt.date
    daily_vol = df.groupby(['date_ny', 'symbol'])['volume'].sum().reset_index()
    max_vol_idx = daily_vol.groupby('date_ny')['volume'].idxmax()
    active_contracts = daily_vol.loc[max_vol_idx, ['date_ny', 'symbol']]
    active_contracts.rename(columns={'symbol': 'active_symbol'}, inplace=True)
    
    df_merged = pd.merge(df, active_contracts, on='date_ny', how='left')
    df_active = df_merged[df_merged['symbol'] == df_merged['active_symbol']].copy()
    
    print(f"Active contract data: {len(df_active):,} rows")
    return df_active


def filter_rth(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Regular Trading Hours only"""
    print("\nFiltering to RTH (09:30-16:00 ET)...")
    
    df = df.copy()
    df.set_index('dt_ny', inplace=True)
    df.sort_index(inplace=True)
    
    # Filter by time
    df['time'] = df.index.time
    start_time = pd.to_datetime(SESSION_START).time()
    end_time = pd.to_datetime(SESSION_END).time()
    
    df_rth = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()
    
    print(f"RTH data: {len(df_rth):,} rows")
    print(f"Date range: {df_rth.index.min()} to {df_rth.index.max()}")
    
    return df_rth


def main():
    parser = argparse.ArgumentParser(description='Donchian Breakout Optimization')
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run with limited combinations for testing')
    parser.add_argument('--max-combos', type=int, default=None,
                       help='Maximum parameter combinations to test')
    parser.add_argument('--full', action='store_true',
                       help='Run full optimization (all combinations)')
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*80)
    print("🚀 DONCHIAN BREAKOUT ML TRADING SYSTEM")
    print("="*80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'TEST' if args.test_mode else 'FULL'}")
    if args.max_combos:
        print(f"Max Combinations: {args.max_combos}")
    print("="*80 + "\n")
    
    # Check data file
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: Data file not found: {DATA_FILE}")
        return
    
    # Load data
    df = load_and_prep_data(DATA_FILE)
    df_active = select_active_contract(df)
    df_rth = filter_rth(df_active)
    
    # Initialize optimizer
    max_combos = args.max_combos if args.max_combos else (50 if args.test_mode else None)
    
    print("\n" + "="*80)
    print("STARTING PARAMETER OPTIMIZATION")
    print("="*80)
    
    optimizer = MLOptimizer(df_rth)
    df_results = optimizer.run_optimization(max_combinations=max_combos)
    
    # Save all results
    results_all_path = os.path.join(ARTIFACTS_DIR, 'donchian_results_all.csv')
    df_results.to_csv(results_all_path, index=False)
    print(f"\n💾 Saved all results to: {results_all_path}")
    
    # Apply filters (60%+ win rate)
    df_filtered = optimizer.apply_filters(
        df_results,
        min_win_rate=60.0,
        min_trades=2000,
        min_sharpe=1.0,
        min_profit_factor=1.5,
        max_drawdown_pct=30.0,
        max_consecutive_losses=5
    )
    
    # Save filtered results
    if len(df_filtered) > 0:
        results_filtered_path = os.path.join(ARTIFACTS_DIR, 'donchian_results_filtered.csv')
        df_filtered.to_csv(results_filtered_path, index=False)
        print(f"💾 Saved filtered results to: {results_filtered_path}")
        
        # Rank strategies
        df_ranked = optimizer.rank_strategies(df_filtered, top_n=10)
        
        # Save top 10
        top10_path = os.path.join(ARTIFACTS_DIR, 'donchian_top10.csv')
        df_ranked.head(10).to_csv(top10_path, index=False)
        print(f"💾 Saved top 10 to: {top10_path}")
        
        # Parameter importance analysis
        optimizer.calculate_parameter_importance(df_results)
        
        # Generate visualizations
        print("\n" + "="*80)
        print("GENERATING VISUALIZATIONS")
        print("="*80)
        
        analyzer = PerformanceAnalyzer(ARTIFACTS_DIR)
        
        # Heatmaps
        print("Creating heatmaps...")
        analyzer.plot_win_rate_heatmap(df_filtered, 'channel_period', 'exit_type')
        analyzer.plot_sharpe_heatmap(df_filtered, 'channel_period', 'stop_type')
        
        # Distributions
        print("Creating distribution plots...")
        analyzer.plot_parameter_distributions(df_filtered)
        
        # Sensitivity analysis
        print("Creating parameter sensitivity plots...")
        analyzer.plot_parameter_sensitivity(df_results)
        
        # Scatter plots
        print("Creating scatter plots...")
        analyzer.plot_scatter_win_rate_vs_sharpe(df_filtered)
        
        # Top strategies comparison
        print("Creating top strategies comparison...")
        analyzer.plot_top_strategies_comparison(df_ranked)
        
        # ATR and VWAP analysis
        print("Creating ATR analysis...")
        analyzer.plot_atr_analysis(df_filtered)
        
        print("Creating VWAP analysis...")
        analyzer.plot_vwap_analysis(df_filtered)
        
        print("Creating combined ATR/VWAP analysis...")
        analyzer.plot_atr_vwap_combined(df_filtered)
        
        # Generate HTML report
        print("\nGenerating HTML report...")
        report_path = analyzer.create_summary_report(df_results, df_filtered, df_ranked)
        
        # Final summary
        print("\n" + "="*80)
        print("✅ OPTIMIZATION COMPLETE!")
        print("="*80)
        print(f"Total combinations tested: {len(df_results)}")
        print(f"Strategies with ≥60% win rate: {len(df_filtered)}")
        print(f"Success rate: {len(df_filtered)/len(df_results)*100:.1f}%")
        
        if len(df_ranked) > 0:
            best = df_ranked.iloc[0]
            print(f"\n🏆 BEST STRATEGY:")
            print(f"   Channel Period: {best['channel_period']}")
            print(f"   Entry Type: {best['entry_type']}")
            print(f"   Exit Type: {best['exit_type']} ({best['exit_param']})")
            print(f"   Stop Type: {best['stop_type']} ({best['stop_param']})")
            print(f"   Session: {best['session_filter']}")
            print(f"   Win Rate: {best['win_rate']:.2f}%")
            print(f"   Sharpe Ratio: {best['sharpe_ratio']:.2f}")
            print(f"   Total P&L: ${best['total_pnl']:,.0f}")
            print(f"   Composite Score: {best['composite_score']:.2f}")
        
        print(f"\n📊 View the full report at: {report_path}")
        print("="*80 + "\n")
        
    else:
        print("\n" + "="*80)
        print("⚠️  NO STRATEGIES PASSED FILTERS")
        print("="*80)
        print("No parameter combinations achieved ≥60% win rate with all filters.")
        print("Consider:")
        print("  1. Relaxing filter criteria")
        print("  2. Expanding parameter search space")
        print("  3. Using different exit/stop strategies")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
