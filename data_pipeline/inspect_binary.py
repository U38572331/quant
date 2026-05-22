
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

for root, dirs, files in os.walk(path):
    if files:
        target = os.path.join(root, files[0])
        print(f"Inspecting: {target}")
        print(f"Size: {os.path.getsize(target)} bytes")
        with open(target, 'rb') as f:
            print(f"Content (hex): {f.read(50).hex()}")
        break
