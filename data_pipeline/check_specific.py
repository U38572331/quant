
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

target_name = "2010-06-06T22_18"
found_path = None

for root, dirs, files in os.walk(path):
    if target_name in files:
        found_path = os.path.join(root, target_name)
        break

if found_path:
    print(f"File found: {found_path}")
    print(f"Size: {os.path.getsize(found_path)}")
    try:
        with open(found_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.read()
            print(f"Read content length: {len(data)}")
            if len(data) > 0:
                print(f"Content preview: {data[:50]}")
    except Exception as e:
        print(f"Error reading: {e}")
else:
    print(f"File {target_name} not found.")
