import pandas as pd
path = r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet'
df = pd.read_parquet(path)
print(df['symbol'].unique())
