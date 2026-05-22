from backtest_orb_vwap_fast import read_dbn_fast
import pandas as pd
import datetime
import struct
import numpy as np

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def check_raw_end():
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        dt = np.dtype([
            ('len', 'u1'), ('rtype', 'u1'), ('pub', '<u2'), ('inst', '<u4'), ('ts', '<u8'),
            ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('vol', '<u8')
        ])
        
        # Seek near end?
        # File size ~ 500MB?
        f.seek(0, 2)
        end_pos = f.tell()
        # Read last 1MB
        seek_pos = max(0, end_pos - 1024*1024)
        f.seek(seek_pos)
        
        # Read but might cut middle of record.
        # Align to block size 56?
        # Records are packed.
        # Better: simple read_from?
        # Just use numpy array from end?
        # Actually, numpy fromfile reads from current pos.
        # Alignment: records are 56 bytes.
        # We need to find sync point?
        # No, from start is safer.
        pass
        
    start_ts = int(pd.Timestamp("2025-12-01", tz="UTC").value)
    
    # Reloading 10M rows takes 3 seconds in numpy.
    
    with open(file_path, "rb") as f:
        f.read(4)
        meta_len = struct.unpack("<I", f.read(4))[0]
        f.read(meta_len)
        
        raw = np.fromfile(f, dtype=dt)
        mask = raw['ts'] > start_ts
        subset = raw[mask]
        print(f"Found {len(subset)} records in Dec 2025.")
        if len(subset) > 0:
            last = subset[-1]
            print("Last Record:")
            print(last)
            print(f"Open Raw: {last['open']}")
        else:
            print("No data at end?")

if __name__ == "__main__":
    check_raw_end()
