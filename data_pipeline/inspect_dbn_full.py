import struct
import sys
import datetime

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def parse_dbn():
    try:
        with open(file_path, "rb") as f:
            # 1. File Header
            header = f.read(4)
            if header != b"DBN\x01":
                print("Not a DBN v1 file")
                return
            
            # 2. Frame Length of Metadata?
            # The next 4 bytes are length of metadata?
            # Actually DBN spec:
            # Bytes 0-3: 'DBN\x1'
            # Bytes 4-7: Length of metadata (u32 little endian)
            meta_len_data = f.read(4)
            meta_len = struct.unpack("<I", meta_len_data)[0]
            print(f"Metadata Length: {meta_len}")
            
            # 3. Read Metadata
            metadata = f.read(meta_len)
            print("Metadata read (skipped details)")
            
            # 4. Read Records
            # Read first record header to see length
            # Header is 16 bytes?
            # Let's peek 1 byte for length
            for i in range(5):
                pos = f.tell()
                length_byte = f.read(1)
                if not length_byte: break
                
                length_words = struct.unpack("B", length_byte)[0]
                record_size = length_words * 4
                
                f.seek(pos)
                record_data = f.read(record_size)
                
                # Parse Header (16 bytes)
                # length(1), rtype(1), pub(2), instr(4), ts(8)
                hdr = struct.unpack("<BBHdQ", record_data[:16]) # wait, ts is u64
                # struct format: B=u8, B=u8, H=u16, I=u32, Q=u64
                hdr = struct.unpack("<BBHIQ", record_data[:16])
                
                length = hdr[0]
                rtype = hdr[1]
                pub_id = hdr[2]
                inst_id = hdr[3]
                ts = hdr[4]
                
                # Check Timestamp
                try:
                    ts_dt = datetime.datetime.fromtimestamp(ts / 1e9, tz=datetime.timezone.utc)
                except:
                    ts_dt = "Invalid"
                    
                print(f"Rec {i}: Len={length}({length*4}b), Type={rtype}, Inst={inst_id}, TS={ts} ({ts_dt})")
                
                # Try to parse OHLCV?
                # Remaining: record_size - 16 bytes.
                # If OHLCV: Open(8), High(8), Low(8), Close(8), Vol(8)?
                payload = record_data[16:]
                if len(payload) >= 40:
                    # int64 * 5 ?
                    ohlcv = struct.unpack("<qqqqQ", payload[:40])
                    # Prices are fixed point 1e-9?
                    o = ohlcv[0] / 1e9
                    h = ohlcv[1] / 1e9
                    l = ohlcv[2] / 1e9
                    c = ohlcv[3] / 1e9
                    v = ohlcv[4]
                    print(f"  OHLCV: O={o}, H={h}, L={l}, C={c}, V={v}")
                
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parse_dbn()
