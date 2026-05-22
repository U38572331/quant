
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

with open("filenames.txt", "w", encoding="utf-8") as f:
    for root, dirs, files in os.walk(path):
        for file in files:
            f.write(file + "\n")
            
print("Dumped filenames to filenames.txt")
