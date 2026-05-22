
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
print(f"Inspecting: {path}")
try:
    if not os.path.exists(path):
        print("Path does not exist")
    elif not os.path.isdir(path):
        print("Path is not a directory")
    else:
        items = os.listdir(path)
        print(f"Found {len(items)} items.")
        files = [f for f in items if f.endswith('.csv')] # Simple filter
        print(f"Found {len(files)} .csv files.")
        
        if items:
            print("First 10 items:")
            for item in items[:10]:
                print(f" - {item}")
        
        if files:
            first_file = files[0]
            full = os.path.join(path, first_file)
            if os.path.isfile(full):
                print(f"Reading sample from {first_file}:")
                with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                     print(f.read(300))
except Exception as e:
    print(f"Error: {e}")
