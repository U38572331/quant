# Quantitative Trading & Financial Engineering Repository

This repository is structured as a "Monorepo" containing several strictly independent quantitative research projects and institutional-grade financial applications. 

To explore a project, please click on its respective directory below. Each directory acts as a standalone software package with its own documentation, mathematical methodology, and visual demonstrations.

## 🚀 Independent Projects Directory

### Systematic Trading Strategies
* **[`strategies/nq_orb_strategy`](strategies/nq_orb_strategy/)** ─ Nasdaq 30m ORB with VWAP Confluence Filters. Includes out-of-sample backtest results and equity curves.

### Financial Dashboards & Data Engineering
* **[`dashboards_and_apps/etf-dividend-analyzer`](dashboards_and_apps/etf-dividend-analyzer/)** ─ DRIP vs. No-DRIP simulation and CAGR analysis dashboard.
* **[`dashboards_and_apps/earnings-monitor`](dashboards_and_apps/earnings-monitor/)** ─ Real-time implied volatility crush monitor for corporate earnings releases.
* **[`dashboards_and_apps/deribit_options_analyzer`](dashboards_and_apps/deribit_options_analyzer/)** ─ Crypto Options GEX (Gamma Exposure) and Order Flow analysis.
* **[`dashboards_and_apps/sec_13f_tracker`](dashboards_and_apps/sec_13f_tracker/)** ─ SEC Edgar automated parsing for tracking institutional hedge fund flows.

---
*Note: All projects rely on shared data parsers and mathematical utilities located in the `data_pipeline/` and `src/` directories of this monorepo.*
