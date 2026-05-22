
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

for root, dirs, files in os.walk(path):
    if files:
        target = os.path.join(root, files[0])
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read(100)
            print("BYTES:", content.replace('\n', '\\n'))
        break
