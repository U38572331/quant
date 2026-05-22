
import os
import time

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

def analyze():
    ts_count = 0
    data_count = 0
    
    first_few = []
    
    with os.scandir(path) as it:
        for i, entry in enumerate(it):
            name = entry.name
            if name.startswith("20") and 'T' in name:
                ts_count += 1
                kind = "TS"
            else:
                data_count += 1
                kind = "DATA"
            
            if i < 20:
                first_few.append((kind, name, entry.stat().st_mtime))
                
            if i % 50000 == 0:
                 print(f"Scanned {i}...", end='\r')

    print(f"\nTotal TS: {ts_count}")
    print(f"Total Data: {data_count}")
    
    print("First 20 items:")
    for kind, name, mtime in first_few:
        print(f"{kind} | {mtime} | {name}")

if __name__ == '__main__':
    analyze()
