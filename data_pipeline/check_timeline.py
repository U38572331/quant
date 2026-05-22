import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
df = df[~df['symbol'].str.contains('-')].copy()
daily_vol = df.groupby([df['ts_event'].dt.date, 'symbol'])['volume'].sum().reset_index()
active = daily_vol.loc[daily_vol.groupby('ts_event')['volume'].idxmax()]
print("Active symbols timeline (sample):\n", active.tail(30).to_string())

# Check for gaps in dates
dates = pd.to_datetime(active['ts_event'].unique())
date_diff = dates.to_series().diff().dt.days
print("\nMax date gap (days):", date_diff.max())
print("Gap dates:\n", dates[date_diff > 4])
