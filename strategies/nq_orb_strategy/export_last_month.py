
import pandas as pd
import datetime
import numpy as np
import backtest_engine

# Define Period
START_DATE = pd.Timestamp("2025-11-12").tz_localize("UTC")
END_DATE = pd.Timestamp("2025-12-15").tz_localize("UTC") # A bit past the end

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

print("--- Loading Data for Dashboard (Last Month) ---")

# Reuse the parser logic from backtest_engine
# We will monkeypatch or just use the function if accessible
# backtest_engine.load_data is a function. 

df_1m = backtest_engine.load_data(file_path)

print(f"Total Data Loaded: {len(df_1m)} rows")

# Filter
df_1m.sort_index(inplace=True)
mask = (df_1m.index >= START_DATE)
df_recent = df_1m[mask].copy()

print(f"Filtered Data (Last Month): {len(df_recent)} rows")

# We need to Calculate VWAP again on this subset? 
# Or can we calculate on the whole and then slice?
# backtest_engine 'calculate_vwap_bands' resets daily. So we can calculate on the subset IF the subset starts at the beginning of a day.
# To be safe, let's calculate on the subset (assuming we include the full starting day).

# Ensure we have the start of the first day
first_day = df_recent.index[0].date()

# Add Date column (Required for VWAP grouping)
df_recent['Date'] = df_recent.index.date

df_recent = backtest_engine.calculate_vwap_bands(df_recent)


# Save to CSV
output_file = "last_month_candle.csv"
df_recent.to_csv(output_file)
print(f"Saved {output_file}")

# Also filter trades
df_trades = pd.read_csv("nq_orb_results.csv")
df_trades['Date'] = pd.to_datetime(df_trades['Date']) # This is date only usually
# Filter trades >= 2025-11-12
df_trades_recent = df_trades[df_trades['Date'] >= pd.Timestamp("2025-11-12")]
df_trades_recent.to_csv("last_month_trades.csv", index=False)
print(f"Saved last_month_trades.csv with {len(df_trades_recent)} trades")
