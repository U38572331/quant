import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['date'] = pd.to_datetime(df['ts_event']).dt.date
unique_dates = df['date'].unique()
print(f"Total unique dates in parquet: {len(unique_dates)}")
