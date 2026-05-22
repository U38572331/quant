import databento as db

dbn_path = r'C:\Users\user\Downloads\glbx-mdp3-20100606-20251212.ohlcv-1m.dbn'

try:
    store = db.DBNStore.from_file(dbn_path)
    print("Dataset:", store.dataset)
    print("Schema:", store.schema)
    print("Symbols in metadata:", store.symbols)
    # Check first few rows
    df = store.to_df()
    print("\nDataFrame Head:\n", df.head())
    print("\nUnique Symbols:", df['symbol'].unique())
except Exception as e:
    print(f"Error: {e}")
