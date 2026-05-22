import sys

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

try:
    with open(file_path, "rb") as f:
        header = f.read(4)
        print(f"Header: {header}")
        # Check for DBN prefix
        if header == b"DBN\x01":
            print("Format: DBN version 1")
        else:
            print(f"Unknown format: {header}")
        
        # Read a bit more to see metadata
        f.seek(0)
        data = f.read(100)
        print(f"Start: {data}")

except Exception as e:
    print(f"Error: {e}")
