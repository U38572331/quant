import databento as db
import pandas as pd
import os

file_path = r"C:\Users\user\Downloads\GLBX-20260503-3DDYMET438\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn"

def inspect_dbn(path):
    if not os.path.exists(path):
        print(f"Error: File not found at {path}")
        return

    print(f"Inspecting file: {path}")
    
    # Load the DBN file
    # We use DBNStore to read the metadata and data
    store = db.DBNStore.from_file(path)
    
    print("\n--- Metadata ---")
    print(f"Dataset: {store.dataset}")
    print(f"Schema: {store.schema}")
    print(f"Stype Config: {store.stype_in} -> {store.stype_out}")
    # print(f"Symbols: {store.symbols}") # This can be very long
    
    # Convert a small chunk to a dataframe
    print("\n--- Data Sample (First 5 rows) ---")
    df = store.to_df()
    print(df.head())
    
    print("\n--- Statistics ---")
    print(f"Total records: {len(df)}")
    print(f"Time range: {df.index.min()} to {df.index.max()}")
    print(f"Unique symbols count: {df['symbol'].nunique() if 'symbol' in df.columns else 'N/A'}")
    if 'symbol' in df.columns:
        print(f"Top 10 symbols by record count:\n{df['symbol'].value_counts().head(10)}")

if __name__ == "__main__":
    inspect_dbn(file_path)
