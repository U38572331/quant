
import os
f = r"C:\Users\user\Downloads\glbx-mdp3-combined.csv"
if os.path.exists(f):
    size_mb = os.path.getsize(f) / (1024*1024)
    print(f"File created: {f}")
    print(f"Size: {size_mb:.2f} MB")
else:
    print("File not found.")
