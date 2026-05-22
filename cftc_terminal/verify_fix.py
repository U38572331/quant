import requests
import urllib.parse
import json

# Mimic the Backend Logic
DATASET_ID = "6dca-aqww"
BASE_URL = "https://publicreporting.cftc.gov/resource/"

def test_fetch(name, code):
    print(f"Testing {name} (Code: {code})...")
    
    # 1. Simulate URL Encoding (The Fix)
    safe_code = urllib.parse.quote(code)
    url = f"{BASE_URL}{DATASET_ID}.json?cftc_contract_market_code='{safe_code}'&$limit=5"
    
    print(f"  URL: {url}")
    
    try:
        r = requests.get(url)
        data = r.json()
        print(f"  Status: {r.status_code}")
        print(f"  Rows Found: {len(data)}")
        if len(data) > 0:
            print(f"  Sample Date: {data[0].get('report_date_as_yyyy_mm_dd')}")
            print("  SUCCESS ✅")
        else:
            print("  FAILURE ❌ (No Data)")
    except Exception as e:
        print(f"  ERROR: {e}")
    print("-" * 50)

if __name__ == "__main__":
    # Test the problematic ones
    test_fetch("Nasdaq Consolidated (Old Link)", "20974+") 
    test_fetch("Nasdaq E-Mini (New Link)", "209742")
    test_fetch("Bitcoin", "133741")
    test_fetch("Gold", "088691")
