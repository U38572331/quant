import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- CONFIGURATION ---
RAW_CSV = r"C:\Users\user\Desktop\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
OUTPUT_PARQUET = r"C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet"

def process_data():
    print(f"Loading raw data from {RAW_CSV}...")
    # Load columns needed for backtesting
    # ts_event, open, high, low, close, volume, symbol
    df = pd.read_csv(RAW_CSV, usecols=['ts_event', 'open', 'high', 'low', 'close', 'volume', 'symbol'])
    
    print("Formatting timestamps...")
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df = df.sort_values('ts_event')
    
    # Simple continuous contract consolidation (using latest symbol per timestamp if duplicates)
    # In practice, one would handle rolls, but for research exploration, we use the merged stream.
    df = df.groupby('ts_event').last().reset_index()
    
    print("Calculating Technical Indicators...")
    # 1. VWAP
    df['date'] = df['ts_event'].dt.date
    df['cum_v'] = df.groupby('date')['volume'].cumsum()
    df['cum_pv'] = df.groupby('date').apply(lambda x: (x['close'] * x['volume']).cumsum(), include_groups=False).reset_index(0, drop=True)
    df['vwap'] = df['cum_pv'] / (df['cum_v'] + 1e-9)
    
    # 2. RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 3. Volume Z-Score
    df['vol_z'] = (df['volume'] - df['volume'].rolling(20).mean()) / (df['volume'].rolling(20).std() + 1e-9)
    
    # 4. ORB Logic (Regular Trading Hours 9:30 - 16:00 ET)
    # Note: CSV is likely UTC. NYC is UTC-5 (EST) or UTC-4 (EDT).
    # We estimate RTH by simple hour filter for discovery (approximate).
    df['hour'] = df['ts_event'].dt.hour
    df['minute'] = df['ts_event'].dt.minute
    
    # Identify Session Start (Approx 14:30 UTC for 9:30 EST)
    df['is_rth'] = ((df['hour'] > 14) | ((df['hour'] == 14) & (df['minute'] >= 30))) & (df['hour'] < 21)
    
    print("Calculating ORB Levels...")
    df['orb_15_h'] = df[df['is_rth']].groupby('date')['high'].transform(lambda x: x.iloc[:15].max())
    df['orb_15_l'] = df[df['is_rth']].groupby('date')['low'].transform(lambda x: x.iloc[:15].min())
    df['orb_30_h'] = df[df['is_rth']].groupby('date')['high'].transform(lambda x: x.iloc[:30].max())
    df['orb_30_l'] = df[df['is_rth']].groupby('date')['low'].transform(lambda x: x.iloc[:30].min())
    df['orb_60_h'] = df[df['is_rth']].groupby('date')['high'].transform(lambda x: x.iloc[:60].max())
    df['orb_60_l'] = df[df['is_rth']].groupby('date')['low'].transform(lambda x: x.iloc[:60].min())
    
    # 5. Session Gap
    # Gap = Today's Open (RTH) - Yesterday's Close (RTH)
    daily_close = df[df['is_rth']].groupby('date')['close'].last().shift(1)
    df['prior_close'] = df['date'].map(daily_close)
    df['session_gap'] = (df['close'] - df['prior_close']) / (df['prior_close'] + 1e-9)
    
    # Cleanup
    df = df.drop(columns=['date', 'cum_v', 'cum_pv', 'hour', 'minute', 'prior_close'])
    
    print(f"Saving to {OUTPUT_PARQUET}...")
    os.makedirs(os.path.dirname(OUTPUT_PARQUET), exist_ok=True)
    df.to_parquet(OUTPUT_PARQUET, compression='snappy')
    print("Data Engineering Complete.")

if __name__ == "__main__":
    process_data()
