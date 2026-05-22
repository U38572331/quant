from backtest_orb_vwap_fast import read_dbn_fast
import pandas as pd
import datetime

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

df = read_dbn_fast(file_path)
if df is not None:
    target = datetime.date(2010, 6, 9)
    df["Date"] = df["Datetime"].dt.date
    day_df = df[df["Date"] == target]
    print(f"Data for {target}:")
    print(day_df.head(10))
    print(day_df.describe())
