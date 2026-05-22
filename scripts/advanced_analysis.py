import pandas as pd
import numpy as np

# Load complete trades without MaxRisk filter to see broader patterns
# Note: I'll use the trades_log.csv from the 'No Filter' run or just re-calculate
# For now, let's look at the current one but keep in mind it's filtered.
df = pd.read_csv('trades_log.csv')
df['Time'] = pd.to_datetime(df['Time'], utc=True)

# Correctly extract Hour and Minute for slotting
df['Entry_Hour'] = df['Time'].dt.hour
df['Entry_Min'] = df['Time'].dt.minute
df['Slot'] = df['Entry_Hour'].map(str) + ":" + (df['Entry_Min'] // 30 * 30).map(str).str.zfill(2)

print("\n=== Profitability by Time Slot ===")
slot_stats = df.groupby('Slot')['PnL'].agg(['count', 'mean', 'sum']).round(2)
print(slot_stats)

df['ExitTime'] = pd.to_datetime(df['ExitTime'], utc=True)
df['Duration'] = (df['ExitTime'] - df['Time']).dt.total_seconds() / 60.0
print(f"\nAverage Duration: {df['Duration'].mean():.2f} mins")
print(f"Median Duration: {df['Duration'].median():.2f} mins")

# We don't have OR Size in the logs yet, I would need to re-run the backtest to save it.
# Let's propose that.
print("\nRecommendation: Analyze OR Size impact.")
