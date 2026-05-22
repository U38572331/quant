
import os
path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
count = 0
for root, dirs, files in os.walk(path):
    for file in files:
        print(os.path.join(root, file))
        count += 1
        if count >= 10: break
    if count >= 10: break
