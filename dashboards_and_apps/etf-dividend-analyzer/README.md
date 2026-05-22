# ETF Dividend Reinvestment Analyzer (DRIP Simulator)

A highly optimized financial simulation web application designed to backtest and visualize the compounding effects of Dividend Reinvestment Plans (DRIP) across major ETFs.

<!-- TODO: 請手動啟動本專案網頁，並截圖儲存為 screenshot.png 放至此目錄下 -->

## 📌 Executive Summary
This application solves the complex problem of accurately backtesting total return vs. price return. By programmatically fetching historical price and dividend tick data from Yahoo Finance, it mathematically aligns dividend ex-dates with end-of-day pricing to simulate exact DRIP compounding.

### Features
* **DRIP vs No-DRIP Comparison**: Isolates the performance delta generated purely from reinvesting dividends versus holding cash.
* **Tax Bracket Adjustments**: Dynamically simulates the drag of dividend taxation on long-term compound annual growth rate (CAGR).
* **Metrics Calculation**: Computes critical quantitative metrics including CAGR, Average Yield, and Net Total Return.

## 🛠️ Technical Implementation
* **Backend Pipeline**: Flask (Python), Pandas, NumPy, yfinance.
* **Frontend Visualization**: Vanilla Javascript, Chart.js, Glassmorphism CSS.
* **Data Engineering**: Chronological index alignment, timezone normalization, and NA imputation for edge-case market days.
