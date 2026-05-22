import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
symbols = df['symbol'].unique()
print("NQ in symbols?", 'NQ' in symbols)
# Also check for symbols with many rows
symbol_counts = df['symbol'].value_counts()
print("\nTop symbols by count:\n", symbol_counts.head(20))
