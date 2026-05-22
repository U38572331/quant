import requests
import time

API_URL = "http://127.0.0.1:8000/api/v1/snapshot/BTC"

print(f"Testing API: {API_URL}")

try:
    start = time.time()
    resp = requests.get(API_URL)
    duration = time.time() - start
    
    print(f"Status Code: {resp.status_code}")
    print(f"Time Taken: {duration:.2f}s")
    
    if resp.status_code == 200:
        data = resp.json()
        print("--- Response Keys ---")
        print(data.keys())
        print("\n--- Metrics ---")
        print(data.get('metrics'))
        print("\n--- Term Structure ---")
        print(data.get('term_structure'))
        print("Success!")
    else:
        print("Error Response:")
        print(resp.text)
except Exception as e:
    print(f"Connection Failed: {e}")
    print("Is the server.py running?")
