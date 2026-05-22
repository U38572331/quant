
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

count = 0
found = 0
for root, dirs, files in os.walk(path):
    for file in files:
        full = os.path.join(root, file)
        try:
            sz = os.path.getsize(full)
            if sz > 0:
                print(f"Found data file: {file} ({sz} bytes)")
                found += 1
                if found >= 5: break
        except Exception as e:
            print(f"Error checking {file}: {e}")
        count += 1
        if count % 1000 == 0:
            print(f"Scanned {count}...", end='\r')
    if found >= 5: break

print(f"\nScanned {count} files. Found {found} non-empty.")
