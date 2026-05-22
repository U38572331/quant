# Real-time Earnings Volatility Monitor

An institutional-grade volatility dashboard for tracking Implied Volatility (IV) crush dynamics around corporate earnings announcements.

<div align="center">
  <img src="screenshot.png" width="90%" alt="Volatility Heatmap">
</div>
*(Actual volatility distribution heatmap)*

## 📌 Technical Overview
Volatility crush trading requires precise timing and accurate measurement of pre-earnings vs. post-earnings IV differentials. This standalone monitor tracks historical IV surface data and maps it against realized post-earnings stock movement.

### Core Analytics
* **IV vs RV Discrepancy**: Plots the spread between what options market makers are pricing in (Implied Volatility) versus actual historical realization.
* **Volatility Cones**: Visualizes current IV percentiles against a rolling 1-year window.
* **Earnings Surprise Overlay**: Correlates EPS surprises with volatility surface collapse.

## 🛠️ System Architecture
* **Data Sources**: Aggregates options chain data to calculate Greeks and IV.
* **UI/UX**: Institutional "dark-mode" data-dense dashboard inspired by professional Bloomberg Terminal environments.
* **Stack**: Python, DataFrames, advanced statistical charting.
