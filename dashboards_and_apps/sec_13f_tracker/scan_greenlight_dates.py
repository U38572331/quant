import requests
import json

CIK = "0001079114" # Greenlight

USER_AGENT = "Individual Investor <analysis@example.com>"
HEADERS = {"User-Agent": USER_AGENT}

url = f"https://data.sec.gov/submissions/CIK{CIK}.json"
try:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    
    recent = data['filings']['recent']
    dates = recent['filingDate']
    
    print(f"Total filings in 'recent': {len(dates)}")
    print(f"Top date: {dates[0]}")
    print(f"Bottom date: {dates[-1]}")
    
    # diverse check
    print(f"Max date: {max(dates)}")
    
    # Check for 2025
    found_2025 = [d for d in dates if '2025' in d]
    print(f"Filings in 2025: {len(found_2025)}")
    if found_2025:
        print(f"  Example: {found_2025[0]}")

except Exception as e:
    print(e)
