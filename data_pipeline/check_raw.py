from backtest_orb_vwap_fast import read_dbn_fast
import pandas as pd
import datetime
import struct
import numpy as np

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

# Reimplement partial read to get access to RAW numpy array
def check_raw_date():
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        # Read all (we have 10M records)
        raw = np.fromfile(f, dtype=dt)
        
        # Find 2010-06-09
        # TS for 2010-06-09 00:00 UTC = 1276041600000000000 (approx)
        start_ts = int(pd.Timestamp("2010-06-09", tz="UTC").value)
        end_ts = int(pd.Timestamp("2010-06-10", tz="UTC").value)
        
        mask = (raw['ts'] >= start_ts) & (raw['ts'] < end_ts)
        subset = raw[mask]
        
        if len(subset) > 0:
            print(f"Found {len(subset)} records.")
            print("First 5 raw:")
            for r in subset[:5]:
                print(r)
                print(f"Open Raw: {r['open']}")
        else:
            print("No data for date.")

if __name__ == "__main__":
    check_raw_date()
