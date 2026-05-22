
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
print(f"Inspecting: {path}")

count = 0
for root, dirs, files in os.walk(path):
    for file in files:
        print(f"File: {file}")
        count += 1
        if count >= 20: break
    if count >= 20: break

if count == 0:
    print("No files found in directory.")
