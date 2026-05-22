
import requests
import json

headers = {
    "User-Agent": "AntigravityDataTerminal/1.0 (contact@example.com)"
}

def test_sec_lookup():
    print("Fetching company_tickers.json...")
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        
        # It comes as distinct entries: "0": {"cik_str":, "ticker":, "title":}
        print(f"Got {len(data)} entries.")
        
        # Convert to list
        companies = list(data.values())
        
        # Search for Apple
        aapl = next((c for c in companies if c['ticker'] == 'AAPL'), None)
        print(f"Apple: {aapl}")
        
        # Search for Berkshire
        bk = [c for c in companies if 'BERKSHIRE' in c['title'].upper()]
        print(f"Berkshire Matches: {len(bk)}")
        if bk:
            print(bk[0])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sec_lookup()
