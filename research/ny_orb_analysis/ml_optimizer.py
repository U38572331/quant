"""
ML-based Parameter Optimization for Donchian Breakout
Performs grid search and applies quantitative filters
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from itertools import product
from donchian_breakout import (
    DonchianBreakout, StrategyParams, EntryType, ExitType, StopType
)


class MLOptimizer:
    """Machine learning-based parameter optimization"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.results = []
        
    def generate_parameter_grid(self) -> List[StrategyParams]:
        """Generate all parameter combinations for grid search"""
        param_grid = {
            'channel_period': [10, 15, 20, 30, 45, 60, 90, 120],
            'entry_type': [EntryType.TOUCH, EntryType.CLOSE],
            'exit_type': [ExitType.FIXED_POINTS, ExitType.R_MULTIPLE, ExitType.TIME_BASED, ExitType.TRAILING],
            'stop_type': [StopType.ATR, StopType.FIXED, StopType.SWING],
            'session_filter': ['full_rth', 'morning_only', 'afternoon_only']
        }
        
        # Exit params depend on exit type
        exit_params = {
            ExitType.FIXED_POINTS: [10, 20, 30, 40, 50, 75, 100],
            ExitType.R_MULTIPLE: [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            ExitType.TIME_BASED: [15, 30, 60, 120],
            ExitType.TRAILING: [5, 10, 15, 20]
        }
        
        # Stop params depend on stop type
        stop_params = {
            StopType.ATR: [1.5, 2.0, 2.5],
            StopType.FIXED: [10, 15, 20, 25],
            StopType.SWING: [0]  # Swing doesn't need param
        }
        
        combinations = []
        
        for channel_period in param_grid['channel_period']:
            for entry_type in param_grid['entry_type']:
                for exit_type in param_grid['exit_type']:
                    for exit_param in exit_params[exit_type]:
                        for stop_type in param_grid['stop_type']:
                            for stop_param in stop_params[stop_type]:
                                for session_filter in param_grid['session_filter']:
                                    params = StrategyParams(
                                        channel_period=channel_period,
                                        entry_type=entry_type,
                                        exit_type=exit_type,
                                        exit_param=exit_param,
                                        stop_type=stop_type,
                                        stop_param=stop_param,
                                        session_filter=session_filter
                                    )
                                    combinations.append(params)
        
        print(f"Generated {len(combinations)} parameter combinations")
        return combinations
    
    def run_optimization(self, max_combinations: Optional[int] = None) -> pd.DataFrame:
        """Run grid search optimization"""
        param_combinations = self.generate_parameter_grid()
        
        if max_combinations and max_combinations < len(param_combinations):
            print(f"Limiting to {max_combinations} combinations for testing")
            np.random.seed(42)
            indices = np.random.choice(len(param_combinations), max_combinations, replace=False)
            param_combinations = [param_combinations[i] for i in indices]
        
        print(f"Running optimization on {len(param_combinations)} combinations...")
        
        for i, params in enumerate(param_combinations):
            print(f"Processing combo {i+1}/{len(param_combinations)}: {params}")
            
            try:
                strategy = DonchianBreakout(params)
                trades = strategy.run_backtest(self.df)
                metrics = strategy.calculate_metrics()
                
                # Calculate ATR and VWAP metrics from trades
                atr_values = [t.atr_at_entry for t in trades if t.atr_at_entry > 0]
                vwap_distances = [t.entry_vs_vwap for t in trades]
                above_vwap = sum(1 for t in trades if t.entry_vs_vwap > 0)
                
                avg_atr_at_entry = np.mean(atr_values) if atr_values else 0.0
                avg_vwap_distance = np.mean(vwap_distances) if vwap_distances else 0.0
                pct_above_vwap = (above_vwap / len(trades) * 100) if trades else 0.0
                
                # Store results
                result = {
                    'channel_period': params.channel_period,
                    'entry_type': params.entry_type.value,
                    'exit_type': params.exit_type.value,
                    'exit_param': params.exit_param,
                    'stop_type': params.stop_type.value,
                    'stop_param': params.stop_param,
                    'session_filter': params.session_filter,
                    'total_trades': metrics.total_trades,
                    'winning_trades': metrics.winning_trades,
                    'losing_trades': metrics.losing_trades,
                    'win_rate': metrics.win_rate,
                    'total_pnl': metrics.total_pnl,
                    'avg_win': metrics.avg_win,
                    'avg_loss': metrics.avg_loss,
                    'profit_factor': metrics.profit_factor,
                    'expectancy': metrics.expectancy,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'max_drawdown': metrics.max_drawdown,
                    'max_drawdown_pct': metrics.max_drawdown_pct,
                    'avg_bars_held': metrics.avg_bars_held,
                    'consecutive_losses_max': metrics.consecutive_losses_max,
                    'recovery_factor': metrics.recovery_factor,
                    'avg_atr_at_entry': avg_atr_at_entry,
                    'avg_vwap_distance': avg_vwap_distance,
                    'pct_above_vwap': pct_above_vwap
                }
                
                self.results.append(result)

                # Incremental save
                temp_df = pd.DataFrame([result])
                save_header = not os.path.exists('donchian_results_incremental.csv')
                temp_df.to_csv('donchian_results_incremental.csv', mode='a', header=save_header, index=False)
                
            except Exception as e:
                print(f"Error with params {params}: {e}")
                continue
        
        df_results = pd.DataFrame(self.results)
        print(f"\nOptimization complete! Tested {len(df_results)} combinations.")
        return df_results
    
    def apply_filters(self, df_results: pd.DataFrame, 
                     min_win_rate: float = 60.0,
                     min_trades: int = 100,
                     min_sharpe: float = 1.0,
                     min_profit_factor: float = 1.5,
                     max_drawdown_pct: float = 30.0,
                     max_consecutive_losses: int = 5) -> pd.DataFrame:
        """Apply quantitative filters to results"""
        
        print("\n" + "="*60)
        print("APPLYING QUANTITATIVE FILTERS")
        print("="*60)
        
        initial_count = len(df_results)
        print(f"Initial strategies: {initial_count}")
        
        # Filter 1: Minimum trades
        df_filtered = df_results[df_results['total_trades'] >= min_trades].copy()
        print(f"After min trades filter (>={min_trades}): {len(df_filtered)}")
        
        # Filter 2: Win rate >= 60%
        df_filtered = df_filtered[df_filtered['win_rate'] >= min_win_rate].copy()
        print(f"After win rate filter (>={min_win_rate}%): {len(df_filtered)}")
        
        # Filter 3: Sharpe ratio
        df_filtered = df_filtered[df_filtered['sharpe_ratio'] >= min_sharpe].copy()
        print(f"After Sharpe ratio filter (>={min_sharpe}): {len(df_filtered)}")
        
        # Filter 4: Profit factor
        df_filtered = df_filtered[df_filtered['profit_factor'] >= min_profit_factor].copy()
        print(f"After profit factor filter (>={min_profit_factor}): {len(df_filtered)}")
        
        # Filter 5: Max drawdown
        df_filtered = df_filtered[df_filtered['max_drawdown_pct'] <= max_drawdown_pct].copy()
        print(f"After max drawdown filter (<={max_drawdown_pct}%): {len(df_filtered)}")
        
        # Filter 6: Consecutive losses
        df_filtered = df_filtered[df_filtered['consecutive_losses_max'] <= max_consecutive_losses].copy()
        print(f"After consecutive losses filter (<={max_consecutive_losses}): {len(df_filtered)}")
        
        # Filter 7: Positive expectancy
        df_filtered = df_filtered[df_filtered['expectancy'] > 0].copy()
        print(f"After positive expectancy filter: {len(df_filtered)}")
        
        print("="*60)
        print(f"FINAL: {len(df_filtered)} strategies passed all filters ({len(df_filtered)/initial_count*100:.1f}%)")
        print("="*60 + "\n")
        
        return df_filtered
    
    def rank_strategies(self, df_filtered: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """Rank strategies by composite score"""
        if len(df_filtered) == 0:
            print("No strategies to rank!")
            return df_filtered
        
        # Normalize metrics to 0-100 scale
        df_ranked = df_filtered.copy()
        
        # Higher is better
        df_ranked['win_rate_norm'] = (df_ranked['win_rate'] - df_ranked['win_rate'].min()) / (df_ranked['win_rate'].max() - df_ranked['win_rate'].min() + 1e-9) * 100
        df_ranked['sharpe_norm'] = (df_ranked['sharpe_ratio'] - df_ranked['sharpe_ratio'].min()) / (df_ranked['sharpe_ratio'].max() - df_ranked['sharpe_ratio'].min() + 1e-9) * 100
        df_ranked['pf_norm'] = (df_ranked['profit_factor'] - df_ranked['profit_factor'].min()) / (df_ranked['profit_factor'].max() - df_ranked['profit_factor'].min() + 1e-9) * 100
        df_ranked['expectancy_norm'] = (df_ranked['expectancy'] - df_ranked['expectancy'].min()) / (df_ranked['expectancy'].max() - df_ranked['expectancy'].min() + 1e-9) * 100
        
        # Lower is better (invert)
        df_ranked['dd_norm'] = (1 - (df_ranked['max_drawdown_pct'] - df_ranked['max_drawdown_pct'].min()) / (df_ranked['max_drawdown_pct'].max() - df_ranked['max_drawdown_pct'].min() + 1e-9)) * 100
        df_ranked['cons_loss_norm'] = (1 - (df_ranked['consecutive_losses_max'] - df_ranked['consecutive_losses_max'].min()) / (df_ranked['consecutive_losses_max'].max() - df_ranked['consecutive_losses_max'].min() + 1e-9)) * 100
        
        # Composite score (weighted average)
        df_ranked['composite_score'] = (
            df_ranked['win_rate_norm'] * 0.25 +
            df_ranked['sharpe_norm'] * 0.25 +
            df_ranked['pf_norm'] * 0.20 +
            df_ranked['expectancy_norm'] * 0.15 +
            df_ranked['dd_norm'] * 0.10 +
            df_ranked['cons_loss_norm'] * 0.05
        )
        
        # Sort by composite score
        df_ranked = df_ranked.sort_values('composite_score', ascending=False)
        
        print(f"\nTop {min(top_n, len(df_ranked))} Strategies by Composite Score:")
        print("="*80)
        
        top_strategies = df_ranked.head(top_n)
        for i, row in top_strategies.iterrows():
            print(f"\nRank #{top_strategies.index.get_loc(i) + 1}")
            print(f"  Channel: {row['channel_period']} | Entry: {row['entry_type']} | Exit: {row['exit_type']}({row['exit_param']})")
            print(f"  Stop: {row['stop_type']}({row['stop_param']}) | Session: {row['session_filter']}")
            print(f"  Win Rate: {row['win_rate']:.1f}% | Trades: {row['total_trades']}")
            print(f"  Sharpe: {row['sharpe_ratio']:.2f} | PF: {row['profit_factor']:.2f} | Expect: ${row['expectancy']:.0f}")
            print(f"  Total P&L: ${row['total_pnl']:,.0f} | Max DD: {row['max_drawdown_pct']:.1f}%")
            print(f"  Composite Score: {row['composite_score']:.2f}")
        
        return df_ranked
    
    def calculate_parameter_importance(self, df_results: pd.DataFrame) -> pd.DataFrame:
        """Analyze which parameters most impact performance"""
        if len(df_results) == 0:
            return pd.DataFrame()
        
        importance = []
        
        for param in ['channel_period', 'entry_type', 'exit_type', 'stop_type', 'session_filter']:
            grouped = df_results.groupby(param).agg({
                'win_rate': ['mean', 'std'],
                'sharpe_ratio': ['mean', 'std'],
                'total_pnl': ['mean', 'std']
            })
            
            # Calculate variance explained (higher = more important)
            win_rate_var = grouped['win_rate']['std'].mean()
            sharpe_var = grouped['sharpe_ratio']['std'].mean()
            pnl_var = grouped['total_pnl']['std'].mean()
            
            importance.append({
                'parameter': param,
                'win_rate_variance': win_rate_var,
                'sharpe_variance': sharpe_var,
                'pnl_variance': pnl_var
            })
        
        df_importance = pd.DataFrame(importance)
        print("\nParameter Importance Analysis:")
        print("="*60)
        print(df_importance.to_string(index=False))
        print("="*60)
        
        return df_importance
