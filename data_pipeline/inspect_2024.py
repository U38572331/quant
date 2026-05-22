import numpy as np
import struct
import pandas as pd

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def inspect_2024():
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        raw = np.fromfile(f, dtype=dt)
        
        # 2024-04-10
        ts_start = int(pd.Timestamp("2024-04-10", tz="UTC").value)
        ts_end = int(pd.Timestamp("2024-04-11", tz="UTC").value)
        
        mask = (raw['ts'] >= ts_start) & (raw['ts'] < ts_end)
        subset = raw[mask]
        
        print(f"Records for 2024-04-10: {len(subset)}")
        if len(subset) > 0:
            scale = 1e-9
            highs = subset['high'] * scale
            lows = subset['low'] * scale
            
            print(f"Max High: {np.max(highs)}")
            print(f"Min Low: {np.min(lows)}")
            
            # Print unusual
            sus = subset[(highs > 30000) | (lows < 1000)]
            if len(sus) > 0:
                print("Found suspicious ticks:")
                for r in sus:
                     print(f"TS: {r['ts']}, H: {r['high']*scale}, L: {r['low']*scale}")

if __name__ == "__main__":
    inspect_2024()
