import sqlite3
import pandas as pd
from backend.data_engine import CFTCDataEngine
import os

db_path = "cftc_data.db"

def check_db():
    if not os.path.exists(db_path):
        print("DB does not exist.")
        return False
    
    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM cot_legacy").fetchone()[0]
        print(f"Row count: {count}")
        
        markets = conn.execute("SELECT DISTINCT market_and_exchange_names FROM cot_legacy LIMIT 5").fetchall()
        print(f"Sample Markets: {markets}")
        
        # Check specifically for Crude
        crude = conn.execute("SELECT COUNT(*) FROM cot_legacy WHERE market_and_exchange_names LIKE '%CRUDE%'").fetchone()[0]
        print(f"Crude rows: {crude}")
        
        return count > 0
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Checking DB...")
    has_data = check_db()
    
    engine = CFTCDataEngine()
    
    if not has_data:
        print("DB invalid or empty. Fetching recent data...")
        count = engine.fetch_recent_data(limit=2000)
        print(f"Fetched {count} rows.")
        check_db()
    else:
        print("DB looks okay.")
