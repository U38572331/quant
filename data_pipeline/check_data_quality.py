import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
print("Unique symbols:", df['symbol'].unique())
print("Price range:", df['close'].min(), df['close'].max())
print("Null values:\n", df.isnull().sum())
