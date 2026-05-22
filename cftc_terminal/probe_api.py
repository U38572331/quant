import requests
import json

DATASET_ID = "6dca-aqww"
BASE_URL = "https://publicreporting.cftc.gov/resource/"

# Keywords to probe
PROBES = [
    "NASDAQ", "DOW JONES", "NIKKEI", "NATURAL GAS", "BITCOIN", "ETHER", "JAPANESE YEN", "SOYBEANS", "WHEAT"
]

def probe():
    print("--- Probing Socrata API ---")
    
    for term in PROBES:
        print(f"\nSearching for '{term}'...")
        # 1. Simplified Search
        # Using $q is safer for general search
        url = f"{BASE_URL}{DATASET_ID}.json?$q={term}&$limit=5&$select=market_and_exchange_names,cftc_contract_market_code"
        try:
            r = requests.get(url)
            try:
                data = r.json()
            except:
                print(f"  FAILED to parse JSON. Raw: {r.text[:200]}")
                continue
                
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
                 print(f"  Unexpected string list: {data[:2]}")
                 continue
                 
            if 'error' in data or (isinstance(data, dict) and 'errorCode' in data):
                print(f"  API ERROR: {data}")
                continue
                
            if not data:
                print("  No matches found via API search.")
                continue
                
            print(f"  Found {len(data)} potential matches:")
            for item in data:
                if not isinstance(item, dict): continue # skip weird items
                name = item.get('market_and_exchange_names', 'Unknown')
                code = item.get('cftc_contract_market_code', 'Unknown')
                print(f"    - [{code}] {name}")
                
                # 2. Try fetching data for this specific code WITH QUOTES
                print(f"      -> Probing history for code {code}...", end=" ")
                hist_url = f"{BASE_URL}{DATASET_ID}.json?cftc_contract_market_code='{code}'&$limit=10"
                hr = requests.get(hist_url)
                if hr.status_code != 200:
                    print(f"HTTP {hr.status_code}")
                else:
                    hdata = hr.json()
                    print(f"Result: {len(hdata)} rows.")
                
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    probe()
