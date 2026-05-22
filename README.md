# Quantitative Trading Research & Systematic Alpha Portfolio

Welcome to my quantitative trading research portfolio. This repository showcases my capabilities in systematic strategy development, statistical arbitrage, market microstructure analysis, and full-stack financial dashboard engineering.

## 🚀 Executive Summary

This portfolio encompasses a rigorous approach to quantitative finance, featuring:
- **Statistical Edge & Hypothesis Testing:** Advanced backtesting of momentum, mean-reversion, and opening range breakout (ORB) strategies with strict adherence to eliminating look-ahead bias and overfitting.
- **Data Engineering & Auditing:** Automated pipelines for fetching, cleaning, and auditing high-resolution tick and minute-level data from institutional sources like Databento and Yahoo Finance.
- **Machine Learning Applications:** Implementing regime-switching models (Markov Chains), Kalman filters for noise reduction, and session volatility prediction to dynamically adjust position sizing and profit targets.
- **Full-Stack Financial Tooling:** Developing interactive, React/Next.js and Flask-based web applications for real-time order flow analysis, options Greek monitoring, and ETF dividend compounding simulations.

---

## 📁 Repository Architecture

The repository has been structured to reflect a professional quantitative research environment:

### `strategies/`
Contains core trading logic, signal generation, and historical backtesting engines.
- **NQ ORB VWAP System:** A robust 30-minute Opening Range Breakout strategy on Nasdaq futures, utilizing 4-VWAP confluence filters and asymmetrical risk-reward optimization.
- **Kalman Filter Models:** Implementation of Kalman filtering for signal smoothing and noise reduction in intraday trading.
- **Intraday Momentum:** Scripts replicating and extending SSRN papers on intraday momentum factor premiums.

### `research/`
Jupyter-style python scripts dedicated to alpha research, factor analysis, and statistical significance testing.
- **Factor Insights & Monte Carlo:** Scripts running Monte Carlo simulations to stress-test equity curves and calculate probability of ruin.
- **Risk Threshold Analysis:** Volatility-adjusted stop-loss and take-profit dynamic modeling.

### `data_pipeline/`
The backbone of the research, ensuring clean and accurate data.
- **Databento Auditing:** Scripts to reconstruct order books and audit tick-level data for missing gaps.
- **Data Quality Checks:** Automated scripts identifying anomalies, verifying R-values, and ensuring symbol continuity across 10-year datasets.

### `analytics_and_viz/`
Tools to translate raw trade logs into actionable insights.
- **Heatmaps & PnL Distributions:** Generation of monthly return heatmaps, drawdown visualizations, and profit distribution charts.
- **Plotly Viewers:** Interactive HTML report generators for deep-diving into individual trade executions against underlying OHLCV data.

### `dashboards_and_apps/`
Production-grade financial web applications and dashboards.
- **Earnings Volatility Monitor:** A real-time tracker analyzing implied vs. realized volatility around earnings releases.
- **ETF Dividend Analyzer:** A Flask application simulating long-term DRIP (Dividend Reinvestment Plan) vs. non-DRIP portfolio growth with dynamic Yahoo Finance data integration.
- **Options Analyzer & 13F Tracker:** Tools for visualizing options flow and tracking institutional holdings.

### `reports/`
Archived outputs of the research, including HTML visualizations, PNG equity curves, and detailed trade logs for peer review.

### `fun_projects/`
A collection of personal programming projects (e.g., game clones, AI logic) demonstrating my broader software engineering passion and proficiency outside of quantitative finance.

---

## 🛠️ Technology Stack

- **Quantitative Research:** Python, Pandas, NumPy, Scikit-Learn, SciPy, Statsmodels.
- **Data Sources:** Databento (Tick/BBO data), yfinance, SEC Edgar, CFTC.
- **Visualization:** Matplotlib, Plotly, Seaborn.
- **Web Applications:** React, Vite, TailwindCSS, Flask.
- **Version Control & CI/CD:** Git, GitHub Actions.

---

## 📈 Contact

Please feel free to explore the code, review the statistical methodologies in the `research/` folder, and test the interactive dashboards in `dashboards_and_apps/`. I am open to discussing the mathematical foundations of these strategies and my software architecture choices in detail.
