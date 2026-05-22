import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
sym = 'NQZ6'
sample = df[df['symbol'] == sym].sort_values('ts_event')
print(f"Sample {sym} data (first 5):\n", sample.head())
print(f"\nSample {sym} data (last 5):\n", sample.tail())
