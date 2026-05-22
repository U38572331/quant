
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

# Find a file
target_file = None
for root, dirs, files in os.walk(path):
    if files:
        target_file = os.path.join(root, files[0])
        break

if target_file:
    print(f"Reading: {target_file}")
    with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
        print(f.read(300))
else:
    print("No files found.")
