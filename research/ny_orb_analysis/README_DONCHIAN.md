# Donchian Breakout ML Trading System

**Professional quantitative trading system** for NQ futures using Donchian Channel Breakout strategy with ML-based parameter optimization.

## Overview

This system implements Donchian Channel Breakout strategy and optimizes parameters to achieve **≥60% win rate** through comprehensive grid search and quantitative filtering.

### Key Features

- ✅ **Donchian Channel Breakout:** Entries on breakouts of N-period highs/lows
- ✅ **Multiple Exit Strategies:** Fixed points, R-multiples, time-based, trailing stops
- ✅ **Flexible Stop Loss:** ATR-based, fixed points, or swing highs/lows
- ✅ **Session Filtering:** Full RTH, morning only, or afternoon only
- ✅ **ML Optimization:** Grid search across 1000+ parameter combinations
- ✅ **Quantitative Filters:** Win rate ≥60%, Sharpe ≥1.0, Profit Factor ≥1.5, etc.
- ✅ **Professional Visualizations:** Heatmaps, distributions, sensitivity analysis
- ✅ **Comprehensive Reporting:** HTML reports with top strategies

## Files

- **`donchian_breakout.py`** - Core strategy engine with backtesting
- **`ml_optimizer.py`** - ML-based parameter optimization and filtering
- **`visualizer.py`** - Professional charts and visualizations
- **`donchian_main.py`** - Main execution script

## Usage

### Quick Test (100 combinations)
```bash
python donchian_main.py --test-mode --max-combos 100
```

### Full Optimization (all combinations)
```bash
python donchian_main.py --full
```

### Custom Combination Limit
```bash
python donchian_main.py --max-combos 500
```

## Parameter Space

- **Channel Period:** 10, 15, 20, 30, 45, 60, 90, 120 bars
- **Entry Type:** Touch channel, Close beyond channel
- **Exit Type:** Fixed points, R-multiple, Time-based, Trailing
- **Exit Params:**
  - Fixed: 10-100 points
  - R-multiple: 0.5-3.0
  - Time: 15-120 minutes
  - Trailing: 5-20 points
- **Stop Type:** ATR-based, Fixed points, Swing highs/lows
- **Session Filter:** Full RTH, Morning only, Afternoon only

## Filter Criteria (60%+ Win Rate)

All strategies must pass:
1. Win Rate ≥ 60%
2. Minimum 100 trades
3. Sharpe Ratio ≥ 1.0
4. Profit Factor ≥ 1.5
5. Max Drawdown ≤ 30%
6. Consecutive Losses ≤ 5
7. Positive Expectancy

## Output Files

All results saved to artifacts directory:
- `donchian_results_all.csv` - All parameter combinations tested
- `donchian_results_filtered.csv` - Only strategies with ≥60% win rate
- `donchian_top10.csv` - Top 10 strategies by composite score
- `donchian_report.html` - Interactive HTML report
- Multiple PNG charts (heatmaps, distributions, comparisons)

## Performance Metrics

- **Win Rate** - Percentage of winning trades
- **Sharpe Ratio** - Risk-adjusted return (annualized)
- **Profit Factor** - Gross profit / Gross loss
- **Expectancy** - Average $ per trade  
- **Max Drawdown** - Largest peak-to-trough decline
- **Recovery Factor** - Total P&L / Max Drawdown

## Example Output

```
🏆 BEST STRATEGY:
   Channel Period: 30
   Entry Type: close
   Exit Type: r_multiple (2.0)
   Stop Type: atr (2.0)
   Session: morning_only
   Win Rate: 65.4%
   Sharpe Ratio: 1.82
   Total P&L: $147,200
   Composite Score: 87.3
```

## System Requirements

- Python 3.7+
- pandas, numpy, matplotlib, seaborn
- ~4GB RAM for full optimization
- Runtime: 5-15 minutes (test mode), 1-3 hours (full)

## Data

Uses NQ futures 1-minute OHLCV data (2010-2019) filtered to Regular Trading Hours (09:30-16:00 ET).

---

**Created:** 2025-12-07  
**Strategy:** Donchian Channel Breakout  
**Objective:** ≥60% Win Rate with Professional Quantitative Analysis
