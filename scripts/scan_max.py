import numpy as np
import struct

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def scan_max():
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        # Iterative read to avoid memory? 500MB is fine.
        raw = np.fromfile(f, dtype=dt)
        
        highs = raw['high'] * 1e-9
        max_h = np.max(highs)
        min_h = np.min(highs)
        
        print(f"Max High: {max_h}")
        print(f"Min High: {min_h}")
        
        # Check counts > 40000
        outliers = np.sum(highs > 40000)
        print(f"Count > 40k: {outliers}")
        
        # Check counts < 0
        neg = np.sum(highs < 0)
        print(f"Count < 0: {neg}")

if __name__ == "__main__":
    scan_max()
