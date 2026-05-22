import databento
import pandas as pd
import json
import os
from datetime import datetime

# File paths
DBN_FILE = "NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_FILE = "chart_data.json"

def process_data():
    print(f"Loading data from {DBN_FILE}...")
    
    # Check if file exists
    if not os.path.exists(DBN_FILE):
        print(f"Error: File {DBN_FILE} not found.")
        return

    try:
        # Load DBN file into DataFrame
        # We need to specify the schema if it's not automatically detected or if we want specific fields
        # Ideally, we verify the schema first, but let's try reading it directly.
        # databento.DBNStore.to_df is a helper; or we can use the reader.
        # Since the file extension is .dbn, we can use databento.read_dbn
        
        # Using read_dbn to get a simplified view
        data = databento.read_dbn(DBN_FILE).to_df()
        
        print(f"Data loaded. Shape: {data.shape}")
        print("Columns:", data.columns)

        # Ensure index is datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            # Sometimes index is named 'ts_event' or similar and is the index
            # If it's already the index (standard for databento df), we are good.
            # If not, we look for 'ts_event'
            pass
            
        # The dataframe usually has a DatetimeIndex named 'ts_event'
        # Let's inspect the index name just in case, but standard Databento DF uses it.
        
        # Resample to 5 minutes
        print("Resampling to 5-minute intervals...")
        
        # OHLCV aggregation
        ohlcv_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # Check available columns. Sometimes they are 'bid_px_00', etc. for MBO, 
        # but for OHLCV-1m schema, they should be standard.
        # However, checking the columns is safer.
        # Standard OHLCV schema columns: open, high, low, close, volume
        
        # We filter only what we need before resampling to save memory if needed
        # But let's assume standard names.
        
        # Databento dataframe usually has columns representing the schema.
        # For OHLCV, it might be 'open', 'high', 'low', 'close', 'volume'.
        
        # We need to handle the case where columns might be different case.
        # Let's just create the logic and handle exceptions if columns are missing.
        
        resampled = data['close'].resample('5min').ohlc()
        # The above 'ohlc()' on a series doesn't handle volume.
        # We need to resample the whole DF with custom mapping.
        
        resampled = data.resample('5min').agg(ohlcv_dict)
        
        # Drop NaN/Empty bins
        resampled = resampled.dropna()
        
        print(f"Resampled data shape: {resampled.shape}")
        
        # Format for Lightweight Charts
        # Expected: { time: string | number, open: number, high: number, low: number, close: number }
        # Time can be a UNIX timestamp (seconds).
        
        chart_data = []
        for index, row in resampled.iterrows():
            # Lightweight charts likes UNIX timestamp in seconds for 'time'
            # Index is Timestamp
            ts = int(index.timestamp())
            
            # Limit to last 5000 candles for demo speed
            # 5000 5-min candles = ~17 days of 24h trading
            MAX_CANDLES = 5000
            
            item = {
                'time': ts,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume'])
            }
            chart_data.append(item)
            
        # Slice to keeping only the last MAX_CANDLES
        if len(chart_data) > MAX_CANDLES:
            print(f"Data too large ({len(chart_data)} records). Keeping last {MAX_CANDLES} records.")
            chart_data = chart_data[-MAX_CANDLES:]
            
        # Write to JSON
        print(f"Writing {len(chart_data)} records to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(chart_data, f)
            
        print("Done.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_data()
