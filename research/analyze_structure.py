
import os

path = r"C:\Users\user\Downloads\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

def analyze():
    print(f"Analyzing {path}")
    root_dirs = []
    root_files = []
    
    try:
        # scan top level only
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir():
                    root_dirs.append(entry.name)
                else:
                    root_files.append(entry.name)
                    
        print(f"Top Level: Dirs={len(root_dirs)}, Files={len(root_files)}")
        
        if len(root_dirs) > 0:
            print(f"Sample Dir: {root_dirs[0]}")
            # Check inside first dir
            subpath = os.path.join(path, root_dirs[0])
            sub_items = os.listdir(subpath)
            print(f"Inside {root_dirs[0]}: {len(sub_items)} items")
            if sub_items:
                print(f" - Item 1: {sub_items[0]}")
                
        if len(root_files) > 0:
            print(f"Sample File: {root_files[0]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    analyze()
