import sqlite3
import pandas as pd
import requests
import urllib.parse
import time

DATASET_ID = "6dca-aqww"
BASE_URL = "https://publicreporting.cftc.gov/resource/"

# Assets to fix and their search terms
TARGETS = {
    'Dow Jones': ['DOW JONES', 'DJIA'],
    'Natural Gas': ['HENRY HUB', 'NATURAL GAS'],
    'Crude Oil': ['CRUDE OIL', 'WTI', 'LIGHT SWEET'],
    'Soybeans': ['SOYBEANS'],
    'Corn': ['CORN'],
    'Wheat': ['WHEAT'],
    'JAPANESE YEN': ['JAPANESE YEN'],
    'EURO': ['EURO FX', 'EURO']
}

def get_candidates(terms):
    conn = sqlite3.connect("cftc_data.db")
    df = pd.read_sql("SELECT DISTINCT market_and_exchange_names, cftc_contract_market_code FROM cot_legacy", conn)
    conn.close()
    
    candidates = []
    for t in terms:
        matches = df[df['market_and_exchange_names'].str.upper().str.contains(t)]
        for _, row in matches.iterrows():
            candidates.append((row['market_and_exchange_names'], row['cftc_contract_market_code']))
    return candidates

def test_socrata(code):
    try:
        url = f"{BASE_URL}{DATASET_ID}.json?cftc_contract_market_code='{urllib.parse.quote(code)}'&$limit=5"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return len(data)
    except:
        pass
    return 0

print(f"{'ASSET':<15} | {'STATUS':<10} | {'BEST CODE'} | {'NAME'}")
print("-" * 80)

for asset, terms in TARGETS.items():
    candidates = get_candidates(terms)
    best_code = None
    best_count = 0
    best_name = ""
    
    # Prioritize unique codes
    unique_candidates = list(set(candidates))
    
    for name, code in unique_candidates:
        # print(f"  Checking {code} ({name[:20]})...")
        count = test_socrata(code)
        if count > 0:
            # Prefer non-consolidated if possible, but data is king
            if count > best_count:
                best_count = count
                best_code = code
                best_name = name
            
            # If we returned 5 (max), and name looks "clean" (no "+"), stop early?
            if count == 5 and "+" not in code:
                 best_code = code
                 best_name = name
                 best_count = count
                 break
    
    if best_code:
        print(f"{asset:<15} | FOUND ({best_count}) | {best_code:<10} | {best_name}")
    else:
        print(f"{asset:<15} | NO DATA    | {'-':<10} | -")
