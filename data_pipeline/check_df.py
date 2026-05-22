from backtest_orb_vwap_fast import read_dbn_fast
import pandas as pd

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

df = read_dbn_fast(file_path)
if df is not None:
    print(df.head())
    print(df.describe())
    
    # Check 2010 values
    print("2010 Data:")
    print(df.iloc[:5])
    
    # Check 2025 values
    print("2025 Data:")
    print(df.iloc[-5:])
