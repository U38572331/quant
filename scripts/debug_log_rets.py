import pandas as pd
import numpy as np
import os

path = r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet'
df = pd.read_parquet(path)
df['ts_event'] = pd.to_datetime(df['ts_event'])
df.set_index('ts_event', inplace=True)
df.sort_index(inplace=True)
df.index = df.index.tz_convert('US/Eastern')
df = df[df['close'] > 100] # NQ should be > 100

rth_df = df.between_time('09:30', '16:00').copy()
rth_df['log_ret'] = np.log(rth_df['close'] / rth_df['close'].shift(1))
print("Log Ret Stats:\n", rth_df['log_ret'].describe())
print("Min Log Ret Row:\n", rth_df.loc[rth_df['log_ret'].idxmin()])
print("Max Log Ret Row:\n", rth_df.loc[rth_df['log_ret'].idxmax()])
