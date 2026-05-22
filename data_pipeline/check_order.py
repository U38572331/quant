
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

with open("order_dump.txt", "w", encoding="utf-8") as f:
    count = 0
    with os.scandir(path) as it:
        for entry in it:
            f.write(entry.name + "\n")
            count += 1
            if count >= 20: break
