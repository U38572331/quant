import os

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

try:
    with open(file_path, 'rb') as f:
        header = f.read(16)
        print(f"Header (hex): {header.hex()}")
        print(f"Header (bytes): {header}")
        
        # Check for ZSTD magic number
        if header.startswith(b'\x28\xb5\x2f\xfd'):
            print("Detected Zstandard compression.")
        elif header.startswith(b'DBN'):
            print("Detected uncompressed DBN.")
        else:
            print("Unknown format.")
            
except Exception as e:
    print(f"Error: {e}")
