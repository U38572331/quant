import sqlite3
import pandas as pd

KEYWORDS = [
    "S&P", "NASDAQ", "DOW", "VIX", "NIKKEI", "GOLD", "SILVER", "COPPER", 
    "OIL", "GAS", "BITCOIN", "ETHER", "EUR", "JPY", "GBP", "AUD", "CAD", 
    "CORN", "SOY", "WHEAT"
]

conn = sqlite3.connect("cftc_data.db")
df = pd.read_sql("SELECT DISTINCT market_and_exchange_names, cftc_contract_market_code FROM cot_legacy", conn)
conn.close()

print(f"{'KEYWORD':<10} | {'MATCHED NAME'}")
print("-" * 60)

for k in KEYWORDS:
    matches = df[df['market_and_exchange_names'].str.upper().str.contains(k)]
    # Print top 3 matches per keyword to help me choose
    for _, row in matches.head(3).iterrows():
        print(f"{k:<10} | {row['market_and_exchange_names']} ({row['cftc_contract_market_code']})")
