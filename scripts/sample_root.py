
import os

source_dir = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

def process():
    print(f"Scanning {source_dir}")
    for root, dirs, files in os.walk(source_dir):
        print(f"Root: {os.path.basename(root)}")
        print(f"File count: {len(files)}")
        print("Sample files:")
        for i, f in enumerate(files):
            print(f" - {f}")
            if i >= 5: break
        
        # Only check the first folder (Root)
        break

if __name__ == '__main__':
    process()
