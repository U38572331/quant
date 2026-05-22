import pandas as pd
import numpy as np
from backtest_orb_vwap_fast import read_dbn_fast

# Re-use read function geometry
file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def verify_reliability():
    print("Loading data for verification...")
    df = read_dbn_fast(file_path)
    if df is None: return

    # 1. Price Scale Verification (Key Dates)
    # External Truth (approx Closing prices from TradingView/Yahoo)
    # 2020-02-19 (Pre-Covid Peak): ~9700
    # 2020-03-23 (Covid Low): ~7000
    # 2021-11-19 (2021 Peak): ~16500
    # 2022-10-13 (2022 Low): ~10500
    # 2024-03-21 (Recent High): ~18300
    
    benchmarks = {
        "2010-06-09": 1700, # Approx
        "2020-02-19": 9700,
        "2020-03-23": 7000,
        "2021-11-19": 16500,
        "2022-10-13": 11000,
        "2024-03-21": 18300
    }
    
    print("\n[1] Historical Price Benchmarking (Daily Close)")
    df["Date"] = df["Datetime"].dt.date
    
    for date_str, expected in benchmarks.items():
        dt = pd.Timestamp(date_str).date()
        day_data = df[df["Date"] == dt]
        if not day_data.empty:
            actual = day_data.iloc[-1]["Close"]
            diff_pct = abs(actual - expected) / expected
            status = "PASS" if diff_pct < 0.1 else "FAIL" # 10% tolerance for variation/contract roll
            print(f"{date_str}: Expected ~{expected}, Got {actual:.2f} (Diff {diff_pct:.2%}) -> {status}")
        else:
            print(f"{date_str}: Data Missing!")

    # 2. Gap Analysis (Missing Business Days)
    print("\n[2] Gap Analysis")
    all_dates = df["Date"].unique()
    all_dates.sort()
    
    # Generate expected business days (NYSE/NASDAQ holiday calendar approx)
    start_d = all_dates[0]
    end_d = all_dates[-1]
    expected_range = pd.date_range(start_d, end_d, freq='B') # Business days
    
    missing = len(expected_range) - len(all_dates)
    coverage = len(all_dates) / len(expected_range)
    
    print(f"Total Unique Trading Days: {len(all_dates)}")
    print(f"Expected Business Days: {len(expected_range)}")
    print(f"Coverage Ratio: {coverage:.2%} (Note: Difference includes Holidays)")
    
    # 3. Trade Fill Quality (from backtest csv)
    print("\n[3] Trade Execution Quality")
    try:
        trades = pd.read_csv("backtest_trades.csv")
        same_bar = trades[trades["Entry"] == trades["Exit"]] # Approx same bar if 0 pnl? No, pnl!=0
        # Actually we don't store duration.
        # But we can check Win Rate vs Long/Short to see if it's suspicious.
        
        # Check "Perfect Tops/Bottoms"
        # Since we use Limit orders, fills are realistic.
        # But if slippage was 0, results are optimistic.
        
        print(f"Total Trades: {len(trades)}")
        print("Slippage Used: 0 points (Optimistic)")
        print("Commission Used: 0 (Gross PnL)")
        
    except:
        print("Could not load trades CSV")

if __name__ == "__main__":
    verify_reliability()
