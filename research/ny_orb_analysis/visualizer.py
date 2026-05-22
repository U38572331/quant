"""
Performance Analysis and Visualization
Creates professional charts and reports
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List
import os


class PerformanceAnalyzer:
    """Analyze and visualize trading performance"""
    
    def __init__(self, artifacts_dir: str):
        self.artifacts_dir = artifacts_dir
        os.makedirs(artifacts_dir, exist_ok=True)
        
        # Set professional style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
    def plot_win_rate_heatmap(self, df_results: pd.DataFrame, param_x: str, param_y: str):
        """Create win rate heatmap for two parameters"""
        if len(df_results) == 0:
            return
        
        # Create pivot table
        pivot = df_results.pivot_table(
            values='win_rate',
            index=param_y,
            columns=param_x,
            aggfunc='mean'
        )
        
        plt.figure(figsize=(14, 8))
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=50,
                   vmin=0, vmax=100, cbar_kws={'label': 'Win Rate (%)'})
        plt.title(f'Win Rate Heatmap: {param_x} vs {param_y}', fontsize=16, fontweight='bold')
        plt.xlabel(param_x.replace('_', ' ').title(), fontsize=12)
        plt.ylabel(param_y.replace('_', ' ').title(), fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, f'heatmap_{param_x}_vs_{param_y}.png'), dpi=150)
        plt.close()
    
    def plot_sharpe_heatmap(self, df_results: pd.DataFrame, param_x: str, param_y: str):
        """Create Sharpe ratio heatmap"""
        if len(df_results) == 0:
            return
        
        pivot = df_results.pivot_table(
            values='sharpe_ratio',
            index=param_y,
            columns=param_x,
            aggfunc='mean'
        )
        
        plt.figure(figsize=(14, 8))
        sns.heatmap(pivot, annot=True, fmt='.2f', cmap='coolwarm', center=0,
                   cbar_kws={'label': 'Sharpe Ratio'})
        plt.title(f'Sharpe Ratio Heatmap: {param_x} vs {param_y}', fontsize=16, fontweight='bold')
        plt.xlabel(param_x.replace('_', ' ').title(), fontsize=12)
        plt.ylabel(param_y.replace('_', ' ').title(), fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, f'sharpe_heatmap_{param_x}_vs_{param_y}.png'), dpi=150)
        plt.close()
    
    def plot_parameter_distributions(self, df_filtered: pd.DataFrame):
        """Plot distributions of key metrics"""
        if len(df_filtered) == 0:
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Distribution of Performance Metrics (Filtered Strategies)', 
                    fontsize=16, fontweight='bold')
        
        # Win Rate
        axes[0, 0].hist(df_filtered['win_rate'], bins=20, color='skyblue', edgecolor='black')
        axes[0, 0].axvline(df_filtered['win_rate'].mean(), color='red', linestyle='--', 
                          label=f'Mean: {df_filtered["win_rate"].mean():.1f}%')
        axes[0, 0].set_xlabel('Win Rate (%)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Win Rate Distribution')
        axes[0, 0].legend()
        axes[0, 0].grid(alpha=0.3)
        
        # Sharpe Ratio
        axes[0, 1].hist(df_filtered['sharpe_ratio'], bins=20, color='lightgreen', edgecolor='black')
        axes[0, 1].axvline(df_filtered['sharpe_ratio'].mean(), color='red', linestyle='--',
                          label=f'Mean: {df_filtered["sharpe_ratio"].mean():.2f}')
        axes[0, 1].set_xlabel('Sharpe Ratio')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Sharpe Ratio Distribution')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)
        
        # Profit Factor
        axes[0, 2].hist(df_filtered['profit_factor'], bins=20, color='lightcoral', edgecolor='black')
        axes[0, 2].axvline(df_filtered['profit_factor'].mean(), color='red', linestyle='--',
                          label=f'Mean: {df_filtered["profit_factor"].mean():.2f}')
        axes[0, 2].set_xlabel('Profit Factor')
        axes[0, 2].set_ylabel('Frequency')
        axes[0, 2].set_title('Profit Factor Distribution')
        axes[0, 2].legend()
        axes[0, 2].grid(alpha=0.3)
        
        # Expectancy
        axes[1, 0].hist(df_filtered['expectancy'], bins=20, color='gold', edgecolor='black')
        axes[1, 0].axvline(df_filtered['expectancy'].mean(), color='red', linestyle='--',
                          label=f'Mean: ${df_filtered["expectancy"].mean():.0f}')
        axes[1, 0].set_xlabel('Expectancy ($)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Expectancy Distribution')
        axes[1, 0].legend()
        axes[1, 0].grid(alpha=0.3)
        
        # Max Drawdown %
        axes[1, 1].hist(df_filtered['max_drawdown_pct'], bins=20, color='plum', edgecolor='black')
        axes[1, 1].axvline(df_filtered['max_drawdown_pct'].mean(), color='red', linestyle='--',
                          label=f'Mean: {df_filtered["max_drawdown_pct"].mean():.1f}%')
        axes[1, 1].set_xlabel('Max Drawdown (%)')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('Max Drawdown % Distribution')
        axes[1, 1].legend()
        axes[1, 1].grid(alpha=0.3)
        
        # Total PnL
        axes[1, 2].hist(df_filtered['total_pnl'], bins=20, color='cyan', edgecolor='black')
        axes[1, 2].axvline(df_filtered['total_pnl'].mean(), color='red', linestyle='--',
                          label=f'Mean: ${df_filtered["total_pnl"].mean():,.0f}')
        axes[1, 2].set_xlabel('Total P&L ($)')
        axes[1, 2].set_ylabel('Frequency')
        axes[1, 2].set_title('Total P&L Distribution')
        axes[1, 2].legend()
        axes[1, 2].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'performance_distributions.png'), dpi=150)
        plt.close()
    
    def plot_parameter_sensitivity(self, df_results: pd.DataFrame):
        """Plot how each parameter affects win rate"""
        if len(df_results) == 0:
            return
        
        params_to_analyze = ['channel_period', 'entry_type', 'exit_type', 'stop_type', 'session_filter']
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Parameter Sensitivity Analysis (Win Rate)', fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        for i, param in enumerate(params_to_analyze):
            grouped = df_results.groupby(param).agg({
                'win_rate': ['mean', 'std', 'count']
            })
            
            x_vals = grouped.index.astype(str)
            y_vals = grouped['win_rate']['mean']
            y_std = grouped['win_rate']['std']
            
            axes[i].bar(x_vals, y_vals, yerr=y_std, capsize=5, color='steelblue', edgecolor='black')
            axes[i].axhline(60, color='red', linestyle='--', linewidth=2, label='60% Threshold')
            axes[i].set_xlabel(param.replace('_', ' ').title(), fontsize=11)
            axes[i].set_ylabel('Avg Win Rate (%)', fontsize=11)
            axes[i].set_title(f'{param.replace("_", " ").title()}', fontsize=12, fontweight='bold')
            axes[i].tick_params(axis='x', rotation=45)
            axes[i].legend()
            axes[i].grid(alpha=0.3, axis='y')
        
        # Hide unused subplot
        axes[5].axis('off')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'parameter_sensitivity.png'), dpi=150)
        plt.close()
    
    def plot_scatter_win_rate_vs_sharpe(self, df_filtered: pd.DataFrame):
        """Scatter plot of win rate vs Sharpe ratio"""
        if len(df_filtered) == 0:
            return
        
        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(df_filtered['win_rate'], df_filtered['sharpe_ratio'],
                            c=df_filtered['total_pnl'], s=df_filtered['total_trades'],
                            alpha=0.6, cmap='viridis', edgecolors='black')
        
        plt.colorbar(scatter, label='Total P&L ($)')
        plt.xlabel('Win Rate (%)', fontsize=12)
        plt.ylabel('Sharpe Ratio', fontsize=12)
        plt.title('Win Rate vs Sharpe Ratio (Bubble size = Total Trades)', 
                 fontsize=14, fontweight='bold')
        plt.axvline(60, color='red', linestyle='--', label='60% Win Rate')
        plt.axhline(1.0, color='orange', linestyle='--', label='Sharpe 1.0')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'scatter_winrate_sharpe.png'), dpi=150)
        plt.close()
    
    def plot_top_strategies_comparison(self, df_top: pd.DataFrame):
        """Compare top strategies across multiple metrics"""
        if len(df_top) == 0:
            return
        
        # Limit to top 10 for readability
        df_plot = df_top.head(10).copy()
        df_plot['strategy_id'] = [f"S{i+1}" for i in range(len(df_plot))]
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Top 10 Strategies Comparison', fontsize=16, fontweight='bold')
        
        # Win Rate
        axes[0, 0].barh(df_plot['strategy_id'], df_plot['win_rate'], color='skyblue', edgecolor='black')
        axes[0, 0].axvline(60, color='red', linestyle='--', linewidth=2)
        axes[0, 0].set_xlabel('Win Rate (%)')
        axes[0, 0].set_title('Win Rate', fontweight='bold')
        axes[0, 0].grid(alpha=0.3, axis='x')
        
        # Sharpe Ratio
        axes[0, 1].barh(df_plot['strategy_id'], df_plot['sharpe_ratio'], color='lightgreen', edgecolor='black')
        axes[0, 1].axvline(1.0, color='orange', linestyle='--', linewidth=2)
        axes[0, 1].set_xlabel('Sharpe Ratio')
        axes[0, 1].set_title('Sharpe Ratio', fontweight='bold')
        axes[0, 1].grid(alpha=0.3, axis='x')
        
        # Total P&L
        axes[1, 0].barh(df_plot['strategy_id'], df_plot['total_pnl'], color='gold', edgecolor='black')
        axes[1, 0].set_xlabel('Total P&L ($)')
        axes[1, 0].set_title('Total P&L', fontweight='bold')
        axes[1, 0].grid(alpha=0.3, axis='x')
        
        # Profit Factor
        axes[1, 1].barh(df_plot['strategy_id'], df_plot['profit_factor'], color='lightcoral', edgecolor='black')
        axes[1, 1].axvline(1.5, color='red', linestyle='--', linewidth=2)
        axes[1, 1].set_xlabel('Profit Factor')
        axes[1, 1].set_title('Profit Factor', fontweight='bold')
        axes[1, 1].grid(alpha=0.3, axis='x')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'top_strategies_comparison.png'), dpi=150)
        plt.close()
    
    def plot_atr_analysis(self, df_filtered: pd.DataFrame):
        """Analyze ATR values and correlation with performance"""
        if len(df_filtered) == 0 or 'avg_atr_at_entry' not in df_filtered.columns:
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('ATR Analysis', fontsize=16, fontweight='bold')
        
        # ATR Distribution
        axes[0].hist(df_filtered['avg_atr_at_entry'], bins=20, color='steelblue', edgecolor='black')
        axes[0].axvline(df_filtered['avg_atr_at_entry'].mean(), color='red', linestyle='--',
                       label=f'Mean: {df_filtered["avg_atr_at_entry"].mean():.1f} pts')
        axes[0].set_xlabel('Average ATR at Entry (points)', fontsize=12)
        axes[0].set_ylabel('Frequency', fontsize=12)
        axes[0].set_title('ATR Distribution', fontweight='bold')
        axes[0].legend()
        axes[0].grid(alpha=0.3)
        
        # ATR vs Win Rate scatter
        scatter = axes[1].scatter(df_filtered['avg_atr_at_entry'], df_filtered['win_rate'],
                                 c=df_filtered['sharpe_ratio'], s=100, alpha=0.6, 
                                 cmap='viridis', edgecolors='black')
        axes[1].set_xlabel('Average ATR at Entry (points)', fontsize=12)
        axes[1].set_ylabel('Win Rate (%)', fontsize=12)
        axes[1].set_title('ATR vs Win Rate (colored by Sharpe)', fontweight='bold')
        axes[1].axhline(60, color='red', linestyle='--', alpha=0.5, label='60% threshold')
        axes[1].legend()
        axes[1].grid(alpha=0.3)
        plt.colorbar(scatter, ax=axes[1], label='Sharpe Ratio')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'atr_analysis.png'), dpi=150)
        plt.close()
    
    def plot_vwap_analysis(self, df_filtered: pd.DataFrame):
        """Analyze VWAP relationships with performance"""
        if len(df_filtered) == 0 or 'pct_above_vwap' not in df_filtered.columns:
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('VWAP Analysis', fontsize=16, fontweight='bold')
        
        # Percentage above VWAP distribution
        axes[0].hist(df_filtered['pct_above_vwap'], bins=20, color='lightcoral', edgecolor='black')
        axes[0].axvline(df_filtered['pct_above_vwap'].mean(), color='red', linestyle='--',
                       label=f'Mean: {df_filtered["pct_above_vwap"].mean():.1f}%')
        axes[0].axvline(50, color='gray', linestyle=':', label='50% (neutral)')
        axes[0].set_xlabel('% Trades Above VWAP', fontsize=12)
        axes[0].set_ylabel('Frequency', fontsize=12)
        axes[0].set_title('Distribution of Entries Above VWAP', fontweight='bold')
        axes[0].legend()
        axes[0].grid(alpha=0.3)
        
        # VWAP distance vs Win Rate
        scatter = axes[1].scatter(df_filtered['avg_vwap_distance'], df_filtered['win_rate'],
                                 c=df_filtered['profit_factor'], s=100, alpha=0.6,
                                 cmap='coolwarm', edgecolors='black')
        axes[1].axvline(0, color='black', linestyle='-', alpha=0.3, linewidth=2)
        axes[1].axhline(60, color='red', linestyle='--', alpha=0.5, label='60% threshold')
        axes[1].set_xlabel('Average Entry Distance from VWAP (points)', fontsize=12)
        axes[1].set_ylabel('Win Rate (%)', fontsize=12)
        axes[1].set_title('VWAP Distance vs Win Rate (colored by PF)', fontweight='bold')
        axes[1].legend()
        axes[1].grid(alpha=0.3)
        plt.colorbar(scatter, ax=axes[1], label='Profit Factor')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'vwap_analysis.png'), dpi=150)
        plt.close()
    
    def plot_atr_vwap_combined(self, df_filtered: pd.DataFrame):
        """Combined ATR and VWAP analysis"""
        if len(df_filtered) == 0 or 'avg_atr_at_entry' not in df_filtered.columns:
            return
        
        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(df_filtered['avg_atr_at_entry'], df_filtered['pct_above_vwap'],
                            c=df_filtered['win_rate'], s=df_filtered['total_trades']/2,
                            alpha=0.6, cmap='RdYlGn', vmin=50, vmax=100, edgecolors='black')
        
        plt.axhline(50, color='gray', linestyle=':', linewidth=2, alpha=0.5, label='50% VWAP neutral')
        plt.colorbar(scatter, label='Win Rate (%)')
        plt.xlabel('Average ATR at Entry (points)', fontsize=12)
        plt.ylabel('% Trades Above VWAP', fontsize=12)
        plt.title('ATR vs VWAP Relationship (Bubble size = Total Trades, Color = Win Rate)',
                 fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifacts_dir, 'atr_vwap_combined.png'), dpi=150)
        plt.close()
    
    
    def create_summary_report(self, df_all: pd.DataFrame, df_filtered: pd.DataFrame, 
                             df_top: pd.DataFrame) -> str:
        """Create HTML summary report"""
        
        html = f"""
        <html>
        <head>
            <title>Donchian Breakout Optimization Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .summary-box {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; background: white; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #3498db; color: white; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
                .metric-label {{ font-size: 12px; color: #7f8c8d; }}
                .highlight {{ background-color: #ffffcc; }}
                img {{ max-width: 100%; margin: 20px 0; border: 1px solid #ddd; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>🚀 Donchian Breakout Trading System - Optimization Report</h1>
            
            <div class="summary-box">
                <h2>Executive Summary</h2>
                <div class="metric">
                    <div class="metric-value">{len(df_all)}</div>
                    <div class="metric-label">Total Combinations Tested</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(df_filtered)}</div>
                    <div class="metric-label">Passed Filters (≥60% WR)</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(df_filtered)/len(df_all)*100:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            </div>
            
            <div class="summary-box">
                <h2>Filter Criteria</h2>
                <ul>
                    <li>✅ Win Rate ≥ 60%</li>
                    <li>✅ Minimum 100 trades (statistical significance)</li>
                    <li>✅ Sharpe Ratio ≥ 1.0</li>
                    <li>✅ Profit Factor ≥ 1.5</li>
                    <li>✅ Max Drawdown ≤ 30%</li>
                    <li>✅ Consecutive Losses ≤ 5</li>
                    <li>✅ Positive Expectancy</li>
                </ul>
            </div>
            
            <div class="summary-box">
                <h2>Top 10 Strategies</h2>
                {df_top.head(10).to_html(index=False, classes='table')}
            </div>
            
            <div class="summary-box">
                <h2>Performance Statistics (Filtered Strategies)</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Mean</th>
                        <th>Std Dev</th>
                        <th>Min</th>
                        <th>Max</th>
                    </tr>
                    <tr>
                        <td>Win Rate (%)</td>
                        <td>{df_filtered['win_rate'].mean():.2f}</td>
                        <td>{df_filtered['win_rate'].std():.2f}</td>
                        <td>{df_filtered['win_rate'].min():.2f}</td>
                        <td>{df_filtered['win_rate'].max():.2f}</td>
                    </tr>
                    <tr>
                        <td>Sharpe Ratio</td>
                        <td>{df_filtered['sharpe_ratio'].mean():.2f}</td>
                        <td>{df_filtered['sharpe_ratio'].std():.2f}</td>
                        <td>{df_filtered['sharpe_ratio'].min():.2f}</td>
                        <td>{df_filtered['sharpe_ratio'].max():.2f}</td>
                    </tr>
                    <tr>
                        <td>Profit Factor</td>
                        <td>{df_filtered['profit_factor'].mean():.2f}</td>
                        <td>{df_filtered['profit_factor'].std():.2f}</td>
                        <td>{df_filtered['profit_factor'].min():.2f}</td>
                        <td>{df_filtered['profit_factor'].max():.2f}</td>
                    </tr>
                    <tr>
                        <td>Total Trades</td>
                        <td>{df_filtered['total_trades'].mean():.0f}</td>
                        <td>{df_filtered['total_trades'].std():.0f}</td>
                        <td>{df_filtered['total_trades'].min():.0f}</td>
                        <td>{df_filtered['total_trades'].max():.0f}</td>
                    </tr>
                </table>
            </div>
            
            <div class="summary-box">
                <h2>ATR and VWAP Analysis</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Mean</th>
                        <th>Std Dev</th>
                        <th>Min</th>
                        <th>Max</th>
                    </tr>
                    <tr>
                        <td>Avg ATR at Entry (points)</td>
                        <td>{df_filtered.get('avg_atr_at_entry', pd.Series([0])).mean():.2f}</td>
                        <td>{df_filtered.get('avg_atr_at_entry', pd.Series([0])).std():.2f}</td>
                        <td>{df_filtered.get('avg_atr_at_entry', pd.Series([0])).min():.2f}</td>
                        <td>{df_filtered.get('avg_atr_at_entry', pd.Series([0])).max():.2f}</td>
                    </tr>
                    <tr>
                        <td>Avg VWAP Distance (points)</td>
                        <td>{df_filtered.get('avg_vwap_distance', pd.Series([0])).mean():.2f}</td>
                        <td>{df_filtered.get('avg_vwap_distance', pd.Series([0])).std():.2f}</td>
                        <td>{df_filtered.get('avg_vwap_distance', pd.Series([0])).min():.2f}</td>
                        <td>{df_filtered.get('avg_vwap_distance', pd.Series([0])).max():.2f}</td>
                    </tr>
                    <tr>
                        <td>% Above VWAP</td>
                        <td>{df_filtered.get('pct_above_vwap', pd.Series([0])).mean():.2f}</td>
                        <td>{df_filtered.get('pct_above_vwap', pd.Series([0])).std():.2f}</td>
                        <td>{df_filtered.get('pct_above_vwap', pd.Series([0])).min():.2f}</td>
                        <td>{df_filtered.get('pct_above_vwap', pd.Series([0])).max():.2f}</td>
                    </tr>
                </table>
            </div>
            
        </body>
        </html>
        """
        
        report_path = os.path.join(self.artifacts_dir, 'donchian_report.html')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n📊 HTML report saved to: {report_path}")
        return report_path
