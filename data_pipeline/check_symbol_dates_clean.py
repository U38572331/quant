import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
clean_df = df[~df['symbol'].str.contains('-')].copy()
symbol_dates = clean_df.groupby('symbol')['ts_event'].agg(['min', 'max', 'count']).sort_values('min')
print("Non-Spread Symbol Date Ranges:\n", symbol_dates.to_string())
