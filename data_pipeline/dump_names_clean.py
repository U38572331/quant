
import os
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
with open("dump_names.txt", "w", encoding="utf-8") as out:
    count = 0
    for root, dirs, files in os.walk(path):
        files.sort()
        for f in files:
            out.write(f + "\n")
            count += 1
            if count >= 20: break
        if count >= 20: break
