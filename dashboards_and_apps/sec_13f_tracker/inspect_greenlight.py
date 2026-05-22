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
    
    print(f"Submissions for CIK {CIK}:")
    for i in range(min(10, len(recent['form']))):
        print(f"{recent['filingDate'][i]} : {recent['form'][i]} - Acc: {recent['accessionNumber'][i]}")
        
except Exception as e:
    print(e)
