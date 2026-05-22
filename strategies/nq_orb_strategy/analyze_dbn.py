import struct
import pandas as pd
import datetime

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def parse_dbn_preview(path):
    with open(path, 'rb') as f:
        # 1. Header: DBN + Version (4 bytes)
        magic = f.read(4) 
        print(f"Magic: {magic}")
        
        # 2. Metadata Length (4 bytes, little endian usually)
        meta_len_data = f.read(4)
        if len(meta_len_data) < 4: return
        meta_len = struct.unpack('<I', meta_len_data)[0]
        print(f"Metadata Length: {meta_len}")
        
        # 3. Read Metadata (Dataset info, Schema, etc.)
        # We assume dataset starts immediately after Header + MetaLen + MetaBody
        # But DBN spec says: Header (4) + Length (4) + Protocol(1) + ... 
        # Actually, let's just skip the 'Meta Length' amount.
        
        # The first 4 bytes were 'DBN\x01'
        # Next 4 bytes are length of the rest of the header/metadata?
        
        f.seek(8) # Already read 8 bytes? No, wait. 
        # file parsing:
        # byte 0-3: DBN\x01
        # byte 4-7: Length of remaining preamble (metadata)
        
        f.seek(4)
        length_bytes = f.read(4)
        body_len = struct.unpack('<I', length_bytes)[0]
        print(f"Preamble Body Length: {body_len}")
        
        # Skip the body
        f.seek(8 + body_len)
        print(f"Seeked to data start at byte: {8 + body_len}")
        
        # Now read records.
        # OHLCV-1m records. 
        # Standard Databenton OHLCV-1m struct (v1):
        # - magc (1 byte)? No.
        # - length (1 byte)
        # - rtype (1 byte)
        # - publisher_id (2 bytes)
        # - product_id (4 bytes)
        # - ts_event (8 bytes, uint64, nanos)
        # - open (8 bytes, int64, fixed dec 9)
        # - high (8 bytes, int64)
        # - low (8 bytes, int64)
        # - close (8 bytes, int64)
        # - volume (8 bytes, int64 / uint64)
        
        # Total size: 1+1+2+4+8+8+8+8+8+8 = 56 bytes? 
        # Let's verify by just reading the first few chunks and printing them.
        
        for i in range(5):
            # Attempt to read generic record header first.
            # DBN Record starts with Length (1 byte, in units of 4 bytes usually?) 
            # DBN records are prefixed with u8 length (in 4-byte words).
            
            pos_start = f.tell()
            head = f.read(1)
            if not head: break
            length_multiplier = struct.unpack('B', head)[0]
            record_size = length_multiplier * 4
            
            # Read full record minus the length byte we just read
            # Actually, standard is: length (u8) is part of the struct? 
            # No, usually "length" is the first field.
            
            f.seek(pos_start)
            record_data = f.read(record_size)
            
            print(f"Record {i}: Size {record_size} bytes")
            
            # Try decoding OHLCV
            # Struct: length(1), rtype(1), pub_id(2), prod_id(4), ts(8), open(8), high(8), low(8), close(8), vol(8)
            # Try decoding OHLCV
            # Struct: length(1), rtype(1), pub_id(2), prod_id(4), ts(8), open(8), high(8), low(8), close(8), vol(8)
            # Total 1+1+2+4+8+8+8+8+8+8 = 56 bytes.
            
            if record_size == 56:
                # fmt: < B(len) B(rtype) H(pub) I(prod) Q(ts) q(O) q(H) q(L) q(C) Q(V)
                # Volume is officially u64 in DBN, usually.
                fmt = '<BBHIQqqqqQ'
                try:
                    data = struct.unpack(fmt, record_data)
                    
                    ts_nanos = data[4]
                    ts_open = pd.to_datetime(ts_nanos, unit='ns', utc=True)
                    
                    open_px = data[5] / 1e9
                    high_px = data[6] / 1e9
                    low_px = data[7] / 1e9
                    close_px = data[8] / 1e9
                    vol = data[9] # Volume is often integer units, sometimes fixed decimal. Usually int unit for futures.
                    
                    print(f"Record {i} | Size: {record_size}")
                    print(f"  Time: {ts_open}")
                    print(f"  O: {open_px}, H: {high_px}, L: {low_px}, C: {close_px}, V: {vol}")
                except Exception as e:
                    print(f"  Error unpacking record {i}: {e}")
            else:
                print(f"Record {i}: Unexpected size {record_size} bytes")

parse_dbn_preview(file_path)
