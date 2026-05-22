
import os
import time

source_dir = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
output_file = r"C:\Users\user\Downloads\glbx-mdp3-combined.csv"

def process():
    if not os.path.exists(source_dir):
        print(f"Error: Source directory not found: {source_dir}")
        return

    print(f"Scanning {source_dir}...")
    print(f"Writing to {output_file}...")
    
    count = 0
    start_time = time.time()
    
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Use os.walk. Sort dirs/files to maintain chronological order
            for root, dirs, files in os.walk(source_dir):
                dirs.sort() # Ensure we visit subdirs in order
                files.sort() # Ensure files are ordered
                
                for file in files:
                    full_path = os.path.join(root, file)
                    
                    # Skip if it's the output file itself (unlikely as it's outside)
                    if os.path.abspath(full_path) == os.path.abspath(output_file):
                        continue
                        
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            data = infile.read()
                            if data:
                                outfile.write(data)
                                if not data.endswith('\n'):
                                    outfile.write('\n')
                                
                        count += 1
                        if count % 10000 == 0:
                            elapsed = time.time() - start_time
                            print(f"Merged {count} files... ({elapsed:.1f}s)")
                            
                    except Exception as e:
                        print(f"Error reading {full_path}: {e}")
                        
        print(f"Done. Merged {count} files into {output_file}")
        print(f"Total time: {time.time() - start_time:.1f}s")
        
    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == '__main__':
    process()
