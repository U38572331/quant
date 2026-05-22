import pandas as pd
import numpy as np
from backtest_orb_vwap_fast import read_dbn_fast

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def quick_verify():
    print("Reading (this may take 10s)...")
    df = read_dbn_fast(file_path)
    if df is None: return

    benchmarks = {
        "2010-06-09": 1700,
        "2020-02-19": 9700,
        "2020-03-23": 7000,
        "2021-11-19": 16500,
        "2022-10-13": 11000,
        "2024-03-21": 18300
    }
    
    print("\n--- PRICE ACCURACY CHECK ---")
    df["Date"] = df["Datetime"].dt.date
    
    for date_str, expected in benchmarks.items():
        dt = pd.Timestamp(date_str).date()
        day_data = df[df["Date"] == dt]
        if not day_data.empty:
            actual = day_data.iloc[-1]["Close"]
            print(f"Date: {date_str} | Expected: {expected} | Actual: {actual:.2f}")
        else:
            print(f"Date: {date_str} | No Data")

if __name__ == "__main__":
    quick_verify()
