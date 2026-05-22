import sqlite3
import pandas as pd

KEYWORDS = ['NASDAQ', 'DOW', 'NIKKEI', 'GAS', 'BITCOIN', 'ETH', 'YEN', 'SOY', 'WHEAT']

conn = sqlite3.connect("cftc_data.db")
df = pd.read_sql("SELECT market_and_exchange_names, cftc_contract_market_code, noncomm_positions_long_all FROM cot_legacy", conn)
conn.close()

print(f"{'NAME':<40} | {'CODE':<10} | {'LONGS (Sample)'}")
print("-" * 70)

for k in KEYWORDS:
    matches = df[df['market_and_exchange_names'].str.upper().str.contains(k)]
    for _, row in matches.iterrows():
        print(f"{row['market_and_exchange_names'][:40]:<40} | {row['cftc_contract_market_code']:<10} | {row['noncomm_positions_long_all']}")
