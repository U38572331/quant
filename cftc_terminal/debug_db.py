import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect("cftc_data.db")
    
    # 1. Check if code exists
    print("Checking for Nasdaq (209747)...")
    df = pd.read_sql("SELECT * FROM cot_legacy WHERE cftc_contract_market_code = '209747'", conn)
    print(f"Found {len(df)} rows.")
    
    if not df.empty:
        # 2. Check for Nulls in critical columns
        print("\nSample Row:")
        print(df.iloc[0])
        
        print("\nChecking for Nulls in calc columns:")
        cols = ['noncomm_positions_long_all', 'noncomm_positions_short_all']
        print(df[cols].isnull().sum())
        
        # 3. Simulate calculation
        try:
            print("\nSimulating Calculation...")
            df['net'] = df['noncomm_positions_long_all'] - df['noncomm_positions_short_all']
            print("Calculation Success.")
        except Exception as e:
            print(f"Calculation FAILED: {e}")
            
    conn.close()
except Exception as e:
    print(f"DB Error: {e}")
