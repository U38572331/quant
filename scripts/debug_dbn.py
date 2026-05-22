import struct
import sys
import datetime

file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

def parse_dbn():
    calc_len = struct.calcsize("<BBHIQ")
    print(f"Struct calcsize: {calc_len}")
    
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"DBN\x01":
                print("Not a DBN v1 file")
                return
            
            meta_len_data = f.read(4)
            meta_len = struct.unpack("<I", meta_len_data)[0]
            print(f"Metadata Length: {meta_len}")
            
            f.read(meta_len) # Skip metadata
            
            pos = f.tell()
            print(f"Data starts at: {pos}")
            
            # Read first byte to get length
            len_byte = f.read(1)
            if not len_byte:
                print("EOF immediately")
                return
            
            len_words = struct.unpack("B", len_byte)[0]
            print(f"First Record Len Words: {len_words}")
            rec_size = len_words * 4
            print(f"First Record Size: {rec_size} bytes")
            
            f.seek(pos)
            data = f.read(rec_size)
            print(f"Read {len(data)} bytes")
            
            # Parse Header
            # Header: Length(1), RType(1), Publisher(2), Instrument(4), TS(8)
            # Total 16 bytes.
            if len(data) >= 16:
                hdr = struct.unpack("<BBHIQ", data[:16])
                print(f"Header Unpacked: {hdr}")
                ts = hdr[4]
                try:
                     print(f"Date: {datetime.datetime.fromtimestamp(ts/1e9, datetime.timezone.utc)}")
                except:
                    pass
                    
                # Payload
                payload = data[16:]
                print(f"Payload len: {len(payload)}")
                # Try OHLCV (5 * 8 = 40 bytes)
                if len(payload) >= 40:
                    ohlcv = struct.unpack("<qqqqQ", payload[:40])
                    print(f"OHLCV Raw: {ohlcv}")
                    print(f"Open: {ohlcv[0]/1e9}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parse_dbn()
