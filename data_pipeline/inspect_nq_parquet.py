import pandas as pd

try:
    df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
    print("Columns:", df.columns.tolist())
    print("Index type:", type(df.index))
    print("\nHead:\n", df.head())
    print("\nTail:\n", df.tail())
    print("\nInfo:\n")
    df.info()
except Exception as e:
    print(f"Error: {e}")
