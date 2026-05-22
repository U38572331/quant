# Binance Orderflow Visualizer

A professional-grade cryptocurrency trading dashboard focusing on Orderflow and Delta Footprint analysis for Binance Futures.

## Features
- Real-time **Delta Footprint** charts.
- **Active Large Order** detection (Whale Bubbles).
- Professional Dark Mode UI.
- Performance optimization using HTML5 Canvas.

## Prerequisites
You need **Node.js** installed on your system to run this application.
Download it here: [https://nodejs.org/](https://nodejs.org/)

## Setup & Run

1. Open a terminal in this directory:
   ```powershell
   cd C:\Users\user\.gemini\antigravity\scratch\binance-orderflow
   ```

2. Install dependencies:
   ```bash
   npm install
   ```
   
   *Note: If you encounter errors, delete `package-lock.json` and try again.*

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to the URL shown (usually `http://localhost:5173`).

## Usage
- **Symbol**: Change the pair in the top right (default BTCUSDT).
- **Threshold**: Adjust the minimum size for "active large orders" in BTC.
- **Navigation**:
  - **Scroll Wheel**: Pan up/down (Price axis).
  - Use the native browser zoom or adjust code constants to zoom in/out (Zoom UI pending).

## Architecture
- **React + Vite**: Frontend framework.
- **TailwindCSS**: UI Styling.
- **WebSocket**: Connects directly to `wss://fstream.binance.com` (No backend required).
- **Canvas API**: Renders the chart for high performance.
