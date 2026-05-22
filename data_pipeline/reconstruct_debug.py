
import os
import time

source_dir = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
output_file = r"C:\Users\user\Downloads\glbx-mdp3-combined.csv"

def process():
    print(f"Source: {source_dir}")
    count = 0
    debug_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Timestamp,Offset,Price,Volume,Symbol\n")
        
        for root, dirs, files in os.walk(source_dir):
            folder_name = os.path.basename(root)
            
            # Debug first few folders
            if debug_count < 10:
                print(f"DEBUG: Visiting {folder_name} | Files: {len(files)}")
                debug_count += 1
            
            if 'T' in folder_name:
                for file in files:
                    # Sanitize file name if needed (remove newlines if any?)
                    row = f"{folder_name},{file}\n"
                    f.write(row)
                    count += 1
                    
            if count % 10000 == 0 and count > 0:
                print(f"Count: {count}", end='\r')

    print(f"\nDone. Processed {count} rows.")

if __name__ == '__main__':
    process()
