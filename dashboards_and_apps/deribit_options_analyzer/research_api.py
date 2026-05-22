import requests
import json

def check_endpoint(url):
    print(f"Checking {url}...")
    try:
        resp = requests.get(url)
        data = resp.json()
        if 'result' in data:
            res = data['result']
            if isinstance(res, list):
                if len(res) > 0:
                    print("Result is list. First item keys:", res[0].keys())
                    print("First item sample:", json.dumps(res[0], indent=2))
                else:
                    print("Result is empty list.")
            elif isinstance(res, dict):
                print("Result is dict. Keys:", res.keys())
                print("Sample:", json.dumps(res, indent=2))
            else:
                print("Result is unknown type:", type(res))
        else:
            print("No result field.")
            print(data)
    except Exception as e:
        print(f"Error: {e}")

print("--- ticker ---")
check_endpoint("https://www.deribit.com/api/v2/public/ticker?instrument_name=BTC-27MAR26-300000-C")

print("--- get_order_book ---")
check_endpoint("https://www.deribit.com/api/v2/public/get_order_book?instrument_name=BTC-27MAR26-300000-C")
