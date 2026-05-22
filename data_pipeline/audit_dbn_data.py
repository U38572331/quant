import databento as db
import pandas as pd
import numpy as np

dbn_path = r'C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn'

print("Loading DBN data...")
store = db.DBNStore.from_file(dbn_path)
df = store.to_df()

# Filter for NQ (E-mini Nasdaq 100) only, exclude spreads
df = df[df['symbol'].str.startswith('NQ') & ~df['symbol'].str.contains('-')].copy()

# Databento index is UTC
df.index = pd.to_datetime(df.index)
df = df.tz_convert('America/New_York')
df['date'] = df.index.date

print(f"Total rows (NQ only): {len(df)}")

# Audit
rth = df[(df.index.time >= pd.to_datetime('09:30').time()) & 
         (df.index.time <= pd.to_datetime('16:00').time())]

# Pick active symbol by volume per day
daily_vol = rth.groupby(['date', 'symbol'])['volume'].sum().reset_index()
active_map = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()].set_index('date')['symbol'].to_dict()

# Apply filter
rth['is_active'] = rth.apply(lambda x: x['symbol'] == active_map.get(x['date']), axis=1)
rth_active = rth[rth['is_active']].copy()

daily_counts = rth_active.groupby('date').size()
missing_days = daily_counts[daily_counts < 380]

print(f"\n--- DataBento Audit (NQ Active) ---")
print(f"Total Trading Days: {len(daily_counts)}")
print(f"Days with missing bars (<380): {len(missing_days)}")
if len(missing_days) > 0:
    print(f"Sample missing days:\n{missing_days.head().to_string()}")

# Save for backtest
rth_active.to_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')
print("\nClean RTH data saved to nq_clean_rth.parquet")
