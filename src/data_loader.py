
import pandas as pd
import numpy as np
import os
from datetime import datetime, time
import pytz

class DataLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """
        Loads data from CSV, parses dates, and filters for NQ symbols.
        """
        print(f"Loading data from {self.file_path}...")
        
        # Determine column names based on file inspection
        # 1: ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol
        
        try:
            self.df = pd.read_csv(self.file_path, parse_dates=['ts_event'])
            print(f"Loaded {len(self.df)} rows.")
        except Exception as e:
            print(f"Error loading CSV: {e}")
            raise

        # Rename columns for convenience
        self.df = self.df.rename(columns={
            'ts_event': 'timestamp',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'symbol': 'Symbol'
        })

        # Filter for NQ only (Just in case other symbols exist)
        self.df = self.df[self.df['Symbol'].str.startswith('NQ')]
        
        # Sort by timestamp
        self.df = self.df.sort_values('timestamp')
        
    def preprocess(self):
        """
        1. Convert timezone to US/Eastern.
        2. Stitch contracts (Volume based dominant contract).
        3. Filter RTH (9:30 - 16:00) generally, but we need 9:30-9:45 for ORB.
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        # 1. Timezone Conversion
        # Assuming original is UTC 'Z'
        if self.df['timestamp'].dt.tz is None:
             self.df['timestamp'] = self.df['timestamp'].dt.tz_localize('UTC')
        
        self.df['timestamp'] = self.df['timestamp'].dt.tz_convert('US/Eastern')
        
        # 2. Stitch Continuous Contract
        print("Stitching continuous contract based on daily volume...")
        
        # Extract Date for grouping
        self.df['Date'] = self.df['timestamp'].dt.date
        
        # Calculate daily volume per symbol
        daily_vol = self.df.groupby(['Date', 'Symbol'])['Volume'].sum().reset_index()
        
        # Find symbol with max volume for each day
        # Sort by Date and Volume desc, then drop duplicates keeping first (max vol)
        dominant_symbols = daily_vol.sort_values(['Date', 'Volume'], ascending=[True, False]).drop_duplicates(subset=['Date'])
        
        # Create a set of (Date, Symbol) tuples to keep
        keep_keys = set(zip(dominant_symbols['Date'], dominant_symbols['Symbol']))
        
        # Filter main df to only keep rows where (Date, Symbol) matches dominant
        # This is a bit slow way: self.df = self.df[self.df.apply(lambda x: (x['Date'], x['Symbol']) in keep_keys, axis=1)]
        # Faster way: Merge
        print(f"Filtering for dominant contracts...")
        self.df = self.df.merge(dominant_symbols[['Date', 'Symbol']], on=['Date', 'Symbol'], how='inner')
        
        print(f"Data stitched. Remaining rows: {len(self.df)}")
        
        # Set index
        self.df.set_index('timestamp', inplace=True)
        
        return self.df

    def get_15m_orb_data(self):
        """
        Extracts 9:30 - 9:45 candle for each day to determine ORB levels.
        """
        if self.df is None:
            self.preprocess()
            
        print("Calculating 15m ORB levels...")
        
        # Filter for trading hours just to be clean, though usually we just look at time
        # We need 9:30:00 to 9:44:59 (inclusive) 1m bars to form the 15m bar
        # OR 9:30 to 9:45 label.
        
        # Method: Resample to 15T (15 min) starting at 9:30
        # First filter RTH mainly
        
        # Create mask for 9:30 ET
        # easier: group by Date, filter times between 09:30 and 09:45
        
        rth_data = self.df.between_time('09:30', '09:44') # 15 mins: 30,31...44 (inclusive)
        
        # Aggregation to get ORB High/Low
        orb_stats = rth_data.groupby(rth_data.index.date).agg({
            'High': 'max',
            'Low': 'min',
            'Open': 'first',
            'Close': 'last',
            'Volume': 'sum'
        })
        
        orb_stats.columns = ['ORB_High', 'ORB_Low', 'ORB_Open', 'ORB_Close', 'ORB_Volume']
        orb_stats.index.name = 'Date'
        
        # Also need "Direction" later
        return orb_stats

if __name__ == "__main__":
    # Test run
    path = r"C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv"
    loader = DataLoader(path)
    loader.load_data()
    df = loader.preprocess()
    print(df.head())
    orb = loader.get_15m_orb_data()
    print(orb.head())
    
    # Save processed chunk for quick verify
    orb.to_csv("src/orb_levels_debug.csv")
