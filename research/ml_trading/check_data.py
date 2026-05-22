
import pandas as pd
import os

file_path = r"C:\Users\user\Desktop\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

try:
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
    else:
        print(f"File found. Size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
        # Read only first few lines to check format


        df = pd.read_csv(file_path, nrows=10)
        with open("info.txt", "w") as f:
            f.write(f"All Columns: {df.columns.tolist()}\n")
            f.write(f"Unique Instruments in sample: {df['instrument_id'].unique()}\n")
            f.write(f"Dtypes:\n{df.dtypes}\n")
            f.write(f"First row: {df.iloc[0].to_dict()}\n")
            
        print("Info written to info.txt")


        
except Exception as e:
    print(f"An error occurred: {e}")
