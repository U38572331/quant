import databento as db
import pandas as pd

file_path = r"C:\Users\user\Downloads\GLBX-20260503-3DDYMET438\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn"

def analyze_nq(path):
    store = db.DBNStore.from_file(path)
    df = store.to_df()
    
    # Filter for NQ symbols
    nq_df = df[df['symbol'].str.contains('NQ', na=False)]
    
    if nq_df.empty:
        print("No NQ symbols found in this file.")
        return

    print(f"\n--- NQ Data Summary ---")
    print(f"Total NQ records: {len(nq_df)}")
    print(f"Unique NQ symbols: {nq_df['symbol'].unique()}")
    print(f"NQ Time range: {nq_df.index.min()} to {nq_df.index.max()}")
    
    # Let's take the most recent NQ symbol and save a sample for visualization
    latest_symbol = nq_df['symbol'].unique()[-1] # Usually the most recent contract
    print(f"Latest NQ symbol identified: {latest_symbol}")
    
    sample = nq_df[nq_df['symbol'] == latest_symbol].tail(1000) # Last 1000 minutes
    sample.to_csv("nq_sample.csv")
    print(f"Saved last 1000 records of {latest_symbol} to nq_sample.csv")

if __name__ == "__main__":
    analyze_nq(file_path)
