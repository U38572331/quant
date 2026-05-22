import struct
import pandas as pd
import datetime

FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def inspect():
    print(f"Inspecting {FILE_PATH}...")
    try:
        with open(FILE_PATH, 'rb') as f:
            magic = f.read(4)
            print(f"Magic: {magic}")
            if not magic.startswith(b'DBN'): return
            
            meta_len_data = f.read(4)
            meta_len = struct.unpack('<I', meta_len_data)[0]
            print(f"Metadata Length: {meta_len}")
            
            f.seek(8 + meta_len)
            
            RECORD_SIZE = 56
            struct_obj = struct.Struct('<BBHIQqqqqQ')
            
            print("Reading first 10 records...")
            for i in range(10):
                chunk = f.read(RECORD_SIZE)
                if not chunk: break
                
                vals = struct_obj.unpack(chunk)
                ts = vals[4]
                ts_dt = pd.to_datetime(ts, unit='ns', utc=True)
                print(f"#{i}: TS={ts} ({ts_dt}) | Type={vals[1]}")
                
            # Check seek to end? No, file is big.
            
            # Check a chunk from middle?
            f.seek(0, 2)
            size = f.tell()
            print(f"File Size: {size / 1024 / 1024:.2f} MB")
            
            # Read last record?
            num_recs = (size - 8 - meta_len) // RECORD_SIZE
            print(f"Approx Records: {num_recs}")
            
            f.seek(8 + meta_len + (num_recs - 5) * RECORD_SIZE)
            print("Reading last 5 records...")
            for i in range(5):
                chunk = f.read(RECORD_SIZE)
                if not chunk: break
                vals = struct_obj.unpack(chunk)
                ts = vals[4]
                ts_dt = pd.to_datetime(ts, unit='ns', utc=True)
                print(f"Last #{i}: TS={ts} ({ts_dt})")
                
    except Exception as e:
        print(e)
        
if __name__ == '__main__':
    inspect()
