
import os
import time

source_dir = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
output_file = r"C:\Users\user\Downloads\glbx-mdp3-combined.csv"

def process():
    print(f"Source: {source_dir}")
    print("Scanning and pairing...")
    
    pairs = []
    current_ts = None
    
    start_time = time.time()
    count = 0
    
    # We use scandir to traverse in filesystem order (assuming interleaving)
    try:
        with os.scandir(source_dir) as it:
            for entry in it:
                name = entry.name
                
                # Check if it looks like a timestamp
                # Format: 2010-06-06T...
                if name.startswith("20") and 'T' in name:
                    current_ts = name
                else:
                    # Assume it's data
                    # If we have a pending timestamp, pair it
                    if current_ts:
                        # Clean up formatting if needed
                        # Timestamp file: 2010-06-06T22_00_00.00
                        # Data file: 1825.500000000,1,NQU0
                        
                        pairs.append((current_ts, name))
                        current_ts = None # Consumed
                    else:
                        # Orphaned data or leading garbage
                        pass
                
                count += 1
                if count % 50000 == 0:
                     print(f"Scanned {count} files...", end='\r')
                     
    except Exception as e:
        print(f"Error during scan: {e}")
        return

    print(f"\nFound {len(pairs)} pairs from {count} files.")
    
    print("Sorting pairs...")
    pairs.sort(key=lambda x: x[0]) # Sort by timestamp
    
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Timestamp,Price,Volume,Symbol\n") # Adjusted header
        for ts, data in pairs:
            # Maybe strip .00 from timestamp if it's seconds decimal?
            # 2010-06-06T22_00_00.00 -> 2010-06-06T22:00:00.00
            # Data file might contain commas.
            # Handle potential Data file format anomalies?
            # data: "1825.5,1,NQU0"
            f.write(f"{ts},{data}\n")
            
    print(f"Done. Wrote {len(pairs)} rows.")
    print(f"Total time: {time.time() - start_time:.1f}s")

if __name__ == '__main__':
    process()
