import pandas as pd
df = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet')
symbols = df['symbol'].unique()
clean_symbols = [s for s in symbols if '-' not in s]
print("Clean symbols:", clean_symbols)

# Check one "clean" symbol
if clean_symbols:
    sample = df[df['symbol'] == clean_symbols[0]]
    print(f"Sample {clean_symbols[0]} price range:", sample['close'].min(), sample['close'].max())
