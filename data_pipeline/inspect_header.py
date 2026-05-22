
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
print(f"Inspecting: {path}")

# Walk to find first csv
first_csv = None
file_count = 0
for root, dirs, files in os.walk(path):
    for file in files:
        if file.endswith(".csv"):
            first_csv = os.path.join(root, file)
            file_count += 1
            if file_count >= 5: break # Count at least 5
    if file_count >= 5: break

print(f"Found {file_count}+ CSV files.")

if first_csv:
    print(f"First CSV: {first_csv}")
    try:
        with open(first_csv, 'r', encoding='utf-8') as f:
            print("--- HEAD START ---")
            for _ in range(5):
                print(f.readline().strip())
            print("--- HEAD END ---")
    except Exception as e:
        print(f"Error reading {first_csv}: {e}")
else:
    print("No CSV files found.")
