import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_api():
    print(f"Testing API at {BASE_URL}...")
    
    # 1. Test Search
    try:
        print("1. Testing /search...")
        r = requests.get(f"{BASE_URL}/search")
        if r.status_code == 200:
            data = r.json()
            print(f"   Success. Found {len(data)} markets.")
            if len(data) > 0:
                print(f"   Sample: {data[0]}")
                first_code = data[0].get('cftc_contract_market_code')
                
                # 2. Test Data for first market
                if first_code:
                    print(f"2. Testing /data/{first_code}...")
                    r2 = requests.get(f"{BASE_URL}/data/{first_code}")
                    if r2.status_code == 200:
                        hist_data = r2.json()
                        print(f"   Success. Found {len(hist_data)} historical records.")
                        print(f"   Latest: {hist_data[-1].get('report_date_as_yyyy_mm_dd')}")
                    else:
                        print(f"   Failed /data: {r2.status_code} - {r2.text}")
                else:
                    print("   Skipping /data test (no code found in search result)")
        else:
            print(f"   Failed /search: {r.status_code} - {r.text}")
            
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    test_api()
