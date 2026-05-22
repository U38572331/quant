import requests
import json

DATASET_ID = "6dca-aqww"
BASE_URL = "https://publicreporting.cftc.gov/resource/"
url = f"{BASE_URL}{DATASET_ID}.json?$limit=5"

try:
    print(f"Fetching from {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    if not data:
        print("FATAL: No data.")
    else:
        keys = data[0].keys()
        print(f"Keys found: {list(keys)}")
        required = ['cftc_contract_market_code', 'report_date_as_yyyy_mm_dd']
        missing = [k for k in required if k not in keys]
        if missing:
            print(f"MISSING COLUMNS: {missing}")
        else:
            print("ALL REQUIRED COLUMNS PRESENT.")
        
except Exception as e:
    print(f"Error: {e}")
