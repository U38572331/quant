import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['date'] = pd.to_datetime(df['ts_event']).dt.date
daily_vol = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
active_map = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()].set_index('date')['symbol'].to_dict()
print("First 5 keys type:", type(list(active_map.keys())[0]))
print("First 5 keys:", list(active_map.keys())[:5])
