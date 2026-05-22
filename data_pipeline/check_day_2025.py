import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
day = '2025-10-01'
sample_day = df[df['ts_event'].dt.date == pd.to_datetime(day).date()]
print(f"Symbols on {day}:\n", sample_day.groupby('symbol')['volume'].sum())
