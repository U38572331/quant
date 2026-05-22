# NQ ORB Strategy Backtest

This project backtests a Long-Only Opening Range Breakout (ORB) strategy on NQ futures data.

## Prerequisites

- **Python 3.10, 3.11, or 3.12** is required.
    - *Note: Python 3.13 is currently NOT supported by the `databenton` library.*
- Data file: `C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn`

## Installation

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Backtest

Run the engine script:
```bash
python backtest_engine.py
```

## Strategy Logic

1. **Session**: RTH (09:30 - 16:15 ET).
2. **Setup**: Calculate High of the 1st hour (09:30-10:30).
3. **Signal**: 5-minute candle Closes above the ORB High.
4. **Entry**: Limit Buy at the current RTH VWAP.
5. **Stop Loss**: VWAP - (1 * ATR).
6. **Take Profit**: Calculated for 1R, 1.5R, and 2R scenarios.
7. **Constraint**: Max 1 trade per session.

## Results

Performance metrics (Win Rate, Total Return in R) will be printed to the console, and a detailed trade log will be saved to `nq_orb_results.csv`.
