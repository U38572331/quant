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
    
    print(f"2025 Filings for CIK {CIK}:")
    count = 0
    for i in range(len(recent['filingDate'])):
        date = recent['filingDate'][i]
        if '2025' in date:
            print(f"{date} : {recent['form'][i]} (Acc: {recent['accessionNumber'][i]})")
            count += 1
            
    if count == 0:
        print("No filings in 2025 found.")
        
except Exception as e:
    print(e)
