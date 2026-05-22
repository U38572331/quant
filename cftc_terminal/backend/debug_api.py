import requests
import pandas as pd

try:
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=1"
    print(f"Fetching {url}")
    resp = requests.get(url)
    data = resp.json()
    if data:
        print("First row keys:")
        print(list(data[0].keys()))
        print("First row values:")
        print(data[0])
    else:
        print("No data received")
except Exception as e:
    print(e)
