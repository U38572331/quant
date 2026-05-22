
import os
import time

source_dir = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
output_file = r"C:\Users\user\Downloads\glbx-mdp3-combined.csv"

def process():
    print(f"Source: {source_dir}")
    print(f"Target: {output_file}")
    
    start_time = time.time()
    count = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Writing a header that makes sense for the observed structure
        # Folder=Timestamp, File=Data (Offset,Price,Vol,Sym)
        f.write("Timestamp,Offset,Price,Volume,Symbol\n")
        
        # Walk
        for root, dirs, files in os.walk(source_dir):
            dirs.sort() # Ensure chronological order
            files.sort() # Ensure sequence order
            
            folder_name = os.path.basename(root)
            
            # Check if this looks like a data folder (contains "T")
            # Example: 2010-06-06T22_04_00
            if 'T' in folder_name:
                timestamp = folder_name.replace('_', ':') # Fix generic timestamp format if needed? 
                # Original: 2010-06-06T22_04_00 
                # Better: 2010-06-06T22:04:00 (Standard ISO)
                # But let's stick to raw or lightweight fix.
                # If valid ISO 8601 uses :, but windows folders use _.
                # I'll replace the LAST two underscores with colons?
                # 22_04_00 -> 22:04:00.
                if len(folder_name) >= 8 and folder_name[-3] == '_' and folder_name[-6] == '_':
                     timestamp = folder_name[:-6] + ':' + folder_name[-5:-3] + ':' + folder_name[-2:]
                
                for file in files:
                    # File: 0,1829.500000000,6,NQM0
                    # We want: timestamp, 0, 1829.5..., 6, NQM0
                    # Just concat.
                    row = f"{timestamp},{file}\n"
                    f.write(row)
                    count += 1
            
            if count % 10000 == 0 and count > 0:
                print(f"Processed {count} rows... ({time.time()-start_time:.1f}s)", end='\r')

    print(f"\nDone. Processed {count} rows.")
    print(f"Total time: {time.time() - start_time:.1f}s")
    
if __name__ == '__main__':
    process()
