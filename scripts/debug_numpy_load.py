import numpy as np
import pandas as pd
import struct

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def debug_load():
    with open(file_path, "rb") as f:
        f.read(4) # magic
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        raw = np.fromfile(f, dtype=dt, count=10)
        print("Raw Records:")
        for r in raw:
            print(r)
            print(f"  Open Raw: {r['open']}")
            print(f"  Open Scaled (1e-6): {r['open'] * 1e-6}")
            print(f"  TS: {r['ts']}")

if __name__ == "__main__":
    debug_load()
