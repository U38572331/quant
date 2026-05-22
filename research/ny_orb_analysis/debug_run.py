
import pandas as pd
import numpy as np
from donchian_breakout import DonchianBreakout, StrategyParams, EntryType, ExitType, StopType

def run_debug():
    # Load data (small chunk)
    print("Loading data...")
    # Adjust path if needed or use HEAD
    try:
        # Read a small subset for speed
        df = pd.read_csv('glbx-mdp3-20100606-20191231.ohlcv-1m.csv', nrows=50000)
    except FileNotFoundError:
        print("Data file not found")
        return

    # Basic preprocessing (mimics donchian_main.py)
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df = df.set_index('ts_event')
    df = df.sort_index()
    print(f"Data range: {df.index.min()} to {df.index.max()}")
    
    # Filter for RTH? No, just run as is. params handle filters.
    
    # Define params (use defaults or common ones)
    params = StrategyParams(
        channel_period=10,
        entry_type=EntryType.TOUCH,
        exit_type=ExitType.FIXED_POINTS,
        exit_param=50.0,
        stop_type=StopType.ATR,
        stop_param=2.0,
        session_filter='full_rth'
    )
    
    print(f"Running strategy with params: {params}")
    
    strategy = DonchianBreakout(params)
    
    # Run backtest - NO TRY/EXCEPT here to see traceback
    trades = strategy.run_backtest(df)
    
    print(f"Trades found: {len(trades)}")
    if trades:
        print(f"First trade: {trades[0]}")

if __name__ == "__main__":
    run_debug()
