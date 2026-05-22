# Deribit Crypto Options Analyzer & GEX Tracker

A sophisticated options flow analyzer specifically built for cryptocurrency derivatives on the Deribit exchange.

<div align="center">
  <img src="screenshot.png" width="90%" alt="Options Confluence Analytics">
</div>
*(Real mathematical confluence surface plot)*

## 📌 Technical Overview
In crypto markets, dealer Gamma Exposure (GEX) heavily dictates short-term price mechanics. This standalone tool calculates the aggregate market-maker gamma positioning across Bitcoin and Ethereum options.

### Core Analytics
* **Net Gamma Profile**: Computes and charts Call vs. Put gamma levels to identify institutional support/resistance walls.
* **Volatility Surface Mapping**: 3D visualization of the implied volatility surface across tenor and moneyness.
* **Open Interest Heatmaps**: Tracks where maximum pain liquidity is concentrated.

## 🛠️ System Architecture
* **Infrastructure**: Real-time REST/Websocket data fetching from Deribit.
* **Math Modeling**: Black-Scholes implementations to derive Greek exposures from live bid-ask spreads.
* **Stack**: Python, Web UI frameworks, high-performance data arrays.
