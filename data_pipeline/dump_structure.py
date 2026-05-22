
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

with open("structure_dump.txt", "w", encoding="utf-8") as f:
    item_count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            f.write(f"ROOT: {os.path.basename(root)} || FILE: {file}\n")
            item_count += 1
            if item_count > 50: break
        if item_count > 50: break
print("Dumped structure.")
