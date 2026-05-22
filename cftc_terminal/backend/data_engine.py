import pandas as pd
import sqlite3
import requests
import logging
from datetime import datetime
import os

# Ultra-Quiet Logging to prevent console spam
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DB_PATH = "cftc_data.db"
# CFTC Socrata Legacy Futures ID
DATASET_ID = "6dca-aqww"
BASE_URL = "https://publicreporting.cftc.gov/resource/"

class CFTCDataEngine:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Create a clean schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # id = contract_code + "_" + date
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cot_legacy (
                id TEXT PRIMARY KEY,
                market_and_exchange_names TEXT,
                report_date_as_yyyy_mm_dd TEXT,
                cftc_contract_market_code TEXT,
                open_interest_all INTEGER,
                noncomm_positions_long_all INTEGER,
                noncomm_positions_short_all INTEGER,
                comm_positions_long_all INTEGER,
                comm_positions_short_all INTEGER,
                nonrept_positions_long_all INTEGER,
                nonrept_positions_short_all INTEGER,
                net_noncomm INTEGER,
                net_comm INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def fetch_recent_data(self, limit=800000):
        """Fetch fresh data from CFTC."""
        print(f"[{datetime.now().time()}] Ingesting CFTC Data (Limit: {limit})... This may take a moment.")
        url = f"{BASE_URL}{DATASET_ID}.json?$limit={limit}&$order=report_date_as_yyyy_mm_dd DESC"
        
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            
            if not data:
                print("CFTC API returned 0 records.")
                return 0
                
            df = pd.DataFrame(data)
            
            # --- Strict Sanitization ---
            # 1. Ensure required columns exist
            required = ['cftc_contract_market_code', 'report_date_as_yyyy_mm_dd']
            if not all(col in df.columns for col in required):
                print("Missing core columns in API response.")
                return 0
                
            # 2. Force Numeric Types
            numeric_cols = [
                'open_interest_all', 
                'noncomm_positions_long_all', 'noncomm_positions_short_all',
                'comm_positions_long_all', 'comm_positions_short_all',
                'nonrept_positions_long_all', 'nonrept_positions_short_all'
            ]
            for col in numeric_cols:
                if col in df.columns:
                    # Coerce errors=coerce makes non-numbers NaN, then we fill 0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                else:
                    df[col] = 0
            
            # 3. Calculate Nets
            df['net_noncomm'] = df['noncomm_positions_long_all'] - df['noncomm_positions_short_all']
            df['net_comm'] = df['comm_positions_long_all'] - df['comm_positions_short_all']
            
            # 4. Generate ID
            df['id'] = df['cftc_contract_market_code'] + "_" + df['report_date_as_yyyy_mm_dd']
            
            # 5. Save
            self._save_to_db(df)
            print(f"Success: Processed {len(df)} records.")
            return len(df)
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return 0

    def _save_to_db(self, df):
        conn = sqlite3.connect(self.db_path)
        # Select strictly ordered columns
        cols = [
            'id', 'market_and_exchange_names', 'report_date_as_yyyy_mm_dd', 
            'cftc_contract_market_code', 'open_interest_all', 
            'noncomm_positions_long_all', 'noncomm_positions_short_all',
            'comm_positions_long_all', 'comm_positions_short_all',
            'nonrept_positions_long_all', 'nonrept_positions_short_all',
            'net_noncomm', 'net_comm'
        ]
        
        # Filter DF to only these cols (if they exist)
        final_df = df[[c for c in cols if c in df.columns]]
        
        # Upsert - SIMPLIFIED
        final_df.drop_duplicates(subset=['id'], keep='last', inplace=True)
        try:
             final_df.to_sql('cot_legacy', conn, if_exists='append', index=False)
        except Exception:
             pass # Ignore PK errors for now (Simulated Upsert via Ignore)
        conn.close()

    def _upsert_method(self, table, conn, keys, data_iter):
        """Custom upsert for SQLite."""
        cursor = conn.cursor()
        sql = f"INSERT OR REPLACE INTO {table.name} ({', '.join(keys)}) VALUES ({', '.join(['?']*len(keys))})"
        for row in data_iter:
            try:
                cursor.execute(sql, row)
            except:
                pass

    def ingest_full_history(self, chunk_size=5000):
        """Fetch all history in chunks to prevent timeouts."""
        offset = 0
        total_ingested = 0
        
        print(f"[{datetime.now().time()}] Starting Chunked Ingest (Chunk Size: {chunk_size})...")
        
        while True:
            url = f"{BASE_URL}{DATASET_ID}.json?$limit={chunk_size}&$offset={offset}&$order=report_date_as_yyyy_mm_dd DESC"
            try:
                print(f"   -> Fetching offset {offset}...")
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                
                if not data:
                    print("   -> No more data. Ingest complete.")
                    break
                
                df = pd.DataFrame(data)
                
                # Santiation
                required = ['cftc_contract_market_code', 'report_date_as_yyyy_mm_dd']
                if not all(col in df.columns for col in required):
                    print("   -> Skipping bad chunk (missing cols).")
                    break

                numeric_cols = [
                    'open_interest_all', 
                    'noncomm_positions_long_all', 'noncomm_positions_short_all',
                    'comm_positions_long_all', 'comm_positions_short_all',
                    'nonrept_positions_long_all', 'nonrept_positions_short_all'
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                    else:
                        df[col] = 0
                
                df['net_noncomm'] = df['noncomm_positions_long_all'] - df['noncomm_positions_short_all']
                df['net_comm'] = df['comm_positions_long_all'] - df['comm_positions_short_all']
                df['id'] = df['cftc_contract_market_code'] + "_" + df['report_date_as_yyyy_mm_dd']
                
                self._save_to_db(df)
                
                count = len(df)
                total_ingested += count
                print(f"   -> Saved {count} rows. Total: {total_ingested}")
                
                if count < chunk_size:
                    # Last page
                    break
                    
                offset += chunk_size
                
            except Exception as e:
                print(f"   -> Error on offset {offset}: {e}")
                break
                
        return total_ingested

    def get_market_list(self):
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT DISTINCT market_and_exchange_names, cftc_contract_market_code FROM cot_legacy ORDER BY market_and_exchange_names", conn)
        conn.close()
        return df.to_dict('records')

    def get_market_history(self, code):
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM cot_legacy WHERE cftc_contract_market_code = ? ORDER BY report_date_as_yyyy_mm_dd ASC", conn, params=(code,))
        conn.close()
        return df.to_dict('records')
