import pandas as pd
import os

path = r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet'
if os.path.exists(path):
    df = pd.read_parquet(path)
    print("Columns:", df.columns.tolist())
    print("Head:\n", df.head())
    print("Time range:", df.index.min(), "to", df.index.max())
    print("Sample freq (first 5 rows index diff):", df.index.to_series().diff().head())
else:
    print("File not found")
