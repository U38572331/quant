
import os
import time

source_dir = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
output_file = r"C:\Users\user\Downloads\glbx-mdp3-combined.csv"

def process():
    print(f"Source: {source_dir}")
    print(f"Output: {output_file}")
    
    rows = []
    
    start_time = time.time()
    
    print("Scanning filenames...")
    try:
        # Use simple os.walk or scandir. os.walk is fine.
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                # Check if it looks like a valid row
                # Expecting: 2010-06-06T... , ...
                if file.startswith("20") and ',' in file:
                    rows.append(file)
            
            # Since files are all in root (proven by analyze), we can stop after root if desired.
            # But safer to walk all just in case.
            
    except Exception as e:
        print(f"Error scanning: {e}")

    print(f"Found {len(rows)} valid row filenames.")
    
    print("Sorting rows...")
    rows.sort()
    
    print("Writing CSV...")
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header - Infer roughly or use standard
        # Timestamp, ?, ?, ?, Open, High, Low, Close, Volume, Symbol
        # The sample showed: ...Z,33,1,26715,1833.5,1833.5,1827.75,1827.75,3,NQU0
        # Columns seem to be: Timestamp, ?, ?, ?, O, H, L, C, ?, Sym
        # I won't guess header names, just write a Generic header or None.
        # User said "combine", implies structure is known. I'll add a generic one.
        f.write("Timestamp,Col1,Col2,Col3,Open,High,Low,Close,Volume,Symbol\n")
        
        for row in rows:
            f.write(row + "\n")
            
    print(f"Done. Wrote {len(rows)} rows.")
    print(f"Total time: {time.time() - start_time:.1f}s")

if __name__ == '__main__':
    process()
