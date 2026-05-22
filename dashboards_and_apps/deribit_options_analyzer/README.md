# Deribit Crypto Options Analyzer & GEX Tracker

A sophisticated options flow analyzer specifically built for cryptocurrency derivatives on the Deribit exchange.

<!-- TODO: 請手動啟動本專案網頁，並截圖儲存為 screenshot.png 放至此目錄下 -->

## 📌 Executive Summary
In crypto markets, dealer Gamma Exposure (GEX) heavily dictates short-term price mechanics. This analyzer calculates the aggregate market-maker gamma positioning across Bitcoin and Ethereum options to predict price pinning, magnetic strike levels, and explosive volatility zones.

### Core Analytics
* **Net Gamma Profile**: Computes and charts Call vs. Put gamma levels to identify institutional support/resistance walls.
* **Volatility Surface Mapping**: 3D visualization of the implied volatility surface across tenor and moneyness.
* **Open Interest Heatmaps**: Tracks where maximum pain liquidity is concentrated.

## 🛠️ Technical Implementation
* **Infrastructure**: Real-time REST/Websocket data fetching from Deribit.
* **Math Modeling**: Black-Scholes implementations to derive Greek exposures from live bid-ask spreads.
* **Stack**: Python, Web UI frameworks, high-performance data arrays.
