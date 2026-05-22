import pandas as pd
import numpy as np

# Load full data
print("Auditing K-line data quality...")
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
df['ts_event'] = pd.to_datetime(df['ts_event'])
df = df.set_index('ts_event').tz_convert('America/New_York')
df['date'] = df.index.date

# Filter for active contracts (we only care about the quality of what we traded)
daily_vol = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
active_map = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()].set_index('date')['symbol'].to_dict()
df['is_active'] = df.apply(lambda x: x['symbol'] == active_map.get(x['date']), axis=1)
df_active = df[df['is_active']].copy()

# 1. Check for Missing Bars in RTH (09:30 - 16:00 = 391 bars)
rth = df_active[(df_active.index.time >= pd.to_datetime('09:30').time()) & 
                (df_active.index.time <= pd.to_datetime('16:00').time())]
daily_counts = rth.groupby('date').size()
missing_days = daily_counts[daily_counts < 380] # Allow a few small gaps

print(f"\n--- Data Integrity Audit ---")
print(f"Total Trading Days: {len(daily_counts)}")
print(f"Days with missing bars (<380): {len(missing_days)}")
if len(missing_days) > 0:
    print(f"Sample missing days:\n{missing_days.head().to_string()}")

# 2. Check for Price Spikes (One-minute move > 1.5%)
rth['pct_move'] = (rth['high'] - rth['low']) / rth['open'] * 100
spikes = rth[rth['pct_move'] > 1.5]
print(f"\n--- Price Anomaly Audit ---")
print(f"Anomalous spikes (>1.5% in 1min): {len(spikes)}")
if len(spikes) > 0:
    print(f"Top 5 spikes:\n{spikes[['symbol', 'open', 'high', 'low', 'close', 'pct_move']].head().to_string()}")

# 3. Check for Spread/Liquidity Issues (Low volume active bars)
low_vol_bars = rth[rth['volume'] < 10]
print(f"\n--- Liquidity Audit ---")
print(f"Bars with extremely low volume (<10): {len(low_vol_bars)}")

# 4. Check for Gaps between Close and next Open
rth['prev_close'] = rth['close'].shift(1)
rth['gap'] = abs(rth['open'] - rth['prev_close']) / rth['prev_close'] * 100
# Filter for gaps within the same day
rth['new_day'] = rth.index.date != pd.Series(rth.index.date).shift(1).values
intra_day_gaps = rth[(~rth['new_day']) & (rth['gap'] > 1.0)]
print(f"\n--- Gap Audit ---")
print(f"Intra-day price gaps (>1%): {len(intra_day_gaps)}")

# Save report
audit_report = {
    'total_days': len(daily_counts),
    'missing_days_count': len(missing_days),
    'spike_count': len(spikes),
    'low_vol_count': len(low_vol_bars),
    'intra_day_gap_count': len(intra_day_gaps)
}
with open(r'C:\Users\user\.gemini\antigravity\scratch\data_audit.json', 'w') as f:
    import json
    json.dump(audit_report, f)
