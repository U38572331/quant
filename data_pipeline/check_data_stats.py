import pandas as pd
import os

path = r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet'
df = pd.read_parquet(path)
print("Volume stats:\n", df['volume'].describe())
print("Price stats:\n", df['close'].describe())
print("NaN count:\n", df[['open', 'high', 'low', 'close', 'volume']].isna().sum())
