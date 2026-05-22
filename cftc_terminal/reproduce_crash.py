from backend.data_engine import CFTCDataEngine
import traceback
import pandas as pd
import json

engine = CFTCDataEngine()

TARGETS = ['124601', '023391', '067651'] # Dow, Gas, Oil

print("--- STARTING CRASH REPRODUCTION ---")

for code in TARGETS:
    print(f"\nTesting Code: {code}")
    try:
        # 1. Simulate DB Fetch
        data = engine.get_data_for_market(code)
        
        # 2. Check basics
        print(f"  Result Type: {type(data)}")
        if isinstance(data, list):
            print(f"  Row Count: {len(data)}")
            if len(data) > 0:
                print(f"  Sample Keys: {list(data[0].keys())[:5]}...")
                # 3. Simulate JSON serialization (FastAPI does this)
                try:
                    json_str = json.dumps(data)
                    print("  JSON Serialization: OK")
                except Exception as je:
                    print(f"  JSON Serialization FAILED: {je}")
        else:
            print("  Data is not a list?")
            
    except Exception as e:
        print(f"  CRASHED: {e}")
        traceback.print_exc()

print("\n--- END ---")
