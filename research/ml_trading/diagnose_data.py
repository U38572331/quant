
import pandas as pd
import os

FILE_PATH = r"C:\Users\user\Desktop\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"

def main():
    print("Reading first 100k rows...")
    df = pd.read_csv(FILE_PATH, nrows=100000)
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    
    # Check bounds
    print(f"Time range: {df['ts_event'].min()} to {df['ts_event'].max()}")
    
    # Check Timezone - assume UTC if Z
    df = df.set_index('ts_event')
    if df.index.tz is None:
        df = df.tz_localize('UTC')
    df_et = df.tz_convert('US/Eastern')
    
    print("Hour distribution in Eastern Time:")
    print(df_et.index.hour.value_counts().sort_index())
    
    # Check specific RTH data
    rth = df_et.between_time("09:30", "16:15")
    print(f"Rows in RTH (09:30-16:15): {len(rth)} out of {len(df)}")
    
    if not rth.empty:
        print("Sample RTH indices:")
        print(rth.index[:5])

if __name__ == "__main__":
    with open("diagnosis.txt", "w") as f:
        import sys
        sys.stdout = f
        main()
