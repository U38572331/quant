import requests
import json

CIK = "0000949509" # Oaktree
# Finding their latest 13F and checking the file list

USER_AGENT = "Individual Investor <analysis@example.com>"
HEADERS = {"User-Agent": USER_AGENT}

def get_submission_history(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=HEADERS)
    return r.json()

history = get_submission_history(CIK)
recent = history['filings']['recent']

# Find latest 13F-HR
acc = None
for i, form in enumerate(recent['form']):
    if form == '13F-HR':
        acc = recent['accessionNumber'][i]
        print(f"Found latest 13F-HR: {acc} (Date: {recent['filingDate'][i]})")
        break

if acc:
    acc_no_hyphen = acc.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{acc_no_hyphen}/index.json"
    print(f"Checking index: {index_url}")
    
    r = requests.get(index_url, headers=HEADERS)
    listing = r.json()
    
    print("\nFiles in directory:")
    for item in listing['directory']['item']:
        print(f" - {item['name']} (Size: {item['size']})")
