import struct
import pandas as pd
import numpy as np
import datetime

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def check_samples():
    print(f"Checking {file_path} ...")
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        raw = np.fromfile(f, dtype=dt)
        print(f"Total Records: {len(raw)}")
        
        # Helper to find date
        def peek_date(date_str):
            ts_start = int(pd.Timestamp(date_str, tz="UTC").value)
            ts_end = int((pd.Timestamp(date_str, tz="UTC") + pd.Timedelta(days=1)).value)
            
            mask = (raw['ts'] >= ts_start) & (raw['ts'] < ts_end)
            subset = raw[mask]
            if len(subset) > 0:
                r = subset[0]
                print(f"\nDate: {date_str}")
                print(f"  Raw Open: {r['open']}")
                print(f"  Raw High: {r['high']}")
                print(f"  Raw Low:  {r['low']}")
                print(f"  Raw Close:{r['close']}")
                
                # Check different scales
                print(f"  Scale 1e-9: {r['close'] * 1e-9}")
                print(f"  Scale 1e-8: {r['close'] * 1e-8}")
                print(f"  Scale 1e-7: {r['close'] * 1e-7}")
            else:
                print(f"\nDate {date_str}: No Data")

        # 1. Start (2010)
        peek_date("2010-06-09")
        
        # 2. 2012 (NQ ~2500)
        peek_date("2012-01-04")
        
        # 3. 2016 (NQ ~4500)
        peek_date("2016-01-04")
        
        # 4. 2020 Covid (Feb/Mar) (NQ ~9000 -> 7000)
        peek_date("2020-03-20")
        
        # 5. Peak 2021 (NQ ~16000)
        peek_date("2021-11-19")
        
        # 6. End 2025? 
        peek_date("2025-12-01")

if __name__ == "__main__":
    check_samples()
