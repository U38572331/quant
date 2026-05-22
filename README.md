# Quantitative Trading & Financial Engineering Repository

This repository is structured as a "Monorepo" containing several strictly independent quantitative research projects and institutional-grade financial applications. 

To explore a project, please click on its respective directory below. Each directory acts as a standalone software package with its own documentation, mathematical methodology, and visual demonstrations.

## 🚀 Core Quantitative Strategies & Math Models

* **[`strategies/nq_orb_strategy`](strategies/nq_orb_strategy/)** ─ Nasdaq 30m ORB with VWAP Confluence Filters. Includes out-of-sample backtest results and equity curves.
* **[`strategies/markov_kalman_models`](strategies/markov_kalman_models/)** ─ Regime-Switching Markov Models & Kalman Filtering. Advanced statistical modeling for dynamic regime adjustment.
* **[`research/monte_carlo_risk_analysis`](research/monte_carlo_risk_analysis/)** ─ Factor Analysis & Monte Carlo Risk Metrics. Rigorous institutional risk management and probability of ruin simulations.

## 📊 Financial Dashboards & Data Engineering

* **[`dashboards_and_apps/etf-dividend-analyzer`](dashboards_and_apps/etf-dividend-analyzer/)** ─ DRIP vs. No-DRIP simulation and CAGR analysis dashboard.
* **[`dashboards_and_apps/earnings-monitor`](dashboards_and_apps/earnings-monitor/)** ─ Real-time implied volatility crush monitor for corporate earnings releases.
* **[`dashboards_and_apps/deribit_options_analyzer`](dashboards_and_apps/deribit_options_analyzer/)** ─ Crypto Options GEX (Gamma Exposure) and Order Flow analysis.
* **[`dashboards_and_apps/sec_13f_tracker`](dashboards_and_apps/sec_13f_tracker/)** ─ SEC Edgar automated parsing for tracking institutional hedge fund flows.

## 📁 Other Notable Engineering Projects

In addition to the core projects above, this repository houses several other research scripts, visualization engines, and specialized terminals:

* **`binance-orderflow/`** ─ Cryptocurrency order book and flow imbalance analytics.
* **`cftc_terminal/`** ─ CoT (Commitment of Traders) report parser and positioning terminal.
* **`flowsurface/`** ─ 3D liquidity rendering and rendering engine.
* **`vulnerability_scout/`** ─ Automated vulnerability scanning and penetration testing automation tools.
* **`nq_chart_viz/`** ─ High-performance tick charting and market microstructure visualization.
* **`fun_projects/`** ─ Miscellaneous technical experiments and coding sandboxes.
* **`data_pipeline/`** ─ Databento tick data processing and normalization infrastructure.

---
*Note: All quantitative strategies rely on shared data parsers and mathematical utilities located in the `data_pipeline/` and `src/` directories of this monorepo.*
