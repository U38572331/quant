import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
symbol_dates = df.groupby('symbol')['ts_event'].agg(['min', 'max', 'count']).sort_values('min')
print("Symbol Date Ranges:\n", symbol_dates.to_string())
