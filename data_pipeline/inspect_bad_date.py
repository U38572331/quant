import numpy as np
import struct
import pandas as pd

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def inspect_date():
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        raw = np.fromfile(f, dtype=dt)
        
        # 2019-05-03
        ts_start = int(pd.Timestamp("2019-05-03", tz="UTC").value)
        ts_end = int(pd.Timestamp("2019-05-04", tz="UTC").value)
        
        mask = (raw['ts'] >= ts_start) & (raw['ts'] < ts_end)
        subset = raw[mask]
        
        print(f"Records for 2019-05-03: {len(subset)}")
        if len(subset) > 0:
            highs = subset['high'] * 1e-9
            lows = subset['low'] * 1e-9
            closes = subset['close'] * 1e-9
            
            print(f"Max High: {np.max(highs)}")
            print(f"Min Low: {np.min(lows)}")
            
            # Print problematic rows (e.g. Low < 0 or High > 20000)
            bad_mask = (highs > 20000) | (lows < 0)
            bad_rows = subset[bad_mask]
            
            if len(bad_rows) > 0:
                print("Found bad rows:")
                for r in bad_rows:
                    print(f"TS: {r['ts']}, H: {r['high']*1e-9}, L: {r['low']*1e-9}")
            else:
                print("No bad rows found on this date.")

if __name__ == "__main__":
    inspect_date()
