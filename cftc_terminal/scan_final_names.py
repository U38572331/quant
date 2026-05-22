import sqlite3
import pandas as pd

# More specific terms to find the "Right" contracts
TERMS = [
    "INDUSTRIAL AVERAGE", # For Dow
    "LIGHT SWEET",        # For WTI
    "HENRY HUB",          # For Gas
    "SOYBEANS",           # For Soy
    "WHEAT",              # For Wheat
    "CORN",               # For Corn
    "JAPANESE YEN",       # For JPY
    "EURO FX"             # For EUR
]

conn = sqlite3.connect("cftc_data.db")
df = pd.read_sql("SELECT DISTINCT market_and_exchange_names, cftc_contract_market_code FROM cot_legacy", conn)
conn.close()

print(f"{'SEARCH TERM':<20} | {'FULL NAME'} | {'CODE'}")
print("-" * 80)

for t in TERMS:
    matches = df[df['market_and_exchange_names'].str.upper().str.contains(t)]
    for _, row in matches.iterrows():
         print(f"{t:<20} | {row['market_and_exchange_names']} | {row['cftc_contract_market_code']}")
