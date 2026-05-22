import pandas as pd
from datetime import datetime

def parse_expiry(instrument_name):
    """
    Parses expiry date from instrument name (e.g., BTC-27MAR26-300000-C).
    Returns TIMESTAMP object localized to UTC 08:00 (Deribit Standard).
    """
    try:
        parts = instrument_name.split('-')
        if len(parts) >= 2:
            date_str = parts[1]
            # Parse date (naive 00:00)
            dt = datetime.strptime(date_str, '%d%b%y')
            # Set to 08:00 UTC (Deribit Expiry Time)
            dt = dt.replace(hour=8, minute=0, second=0)
            return pd.Timestamp(dt).tz_localize('UTC')
    except Exception as e:
        pass
    return None

def parse_strike(instrument_name):
    try:
        parts = instrument_name.split('-')
        if len(parts) >= 3:
            return float(parts[2])
    except:
        pass
    return 0.0

def parse_type(instrument_name):
    if instrument_name.endswith('-C'):
        return 'call'
    elif instrument_name.endswith('-P'):
        return 'put'
    return 'unknown'

def enrich_data(instruments_df, summary_df, real_spot=None):
    """
    Merges instruments and summary data, adds expiry, strike, time to expiry.
    Forces Underlying Price to be Real Spot if provided.
    """
    if instruments_df.empty or summary_df.empty:
        return pd.DataFrame()

    # Merge on instrument_name
    df = pd.merge(instruments_df, summary_df, on='instrument_name', how='inner', suffixes=('', '_summary'))
    
    # Parse details
    df['expiry_date'] = df['instrument_name'].apply(parse_expiry)
    df['strike'] = df['instrument_name'].apply(parse_strike)
    df['instrument_type'] = df['instrument_name'].apply(parse_type)
    
    # Calculate time to expiry in years
    # Use exact UTC now
    now = pd.Timestamp.now(tz='UTC')
    
    # Check for invalid expiries (None)
    df = df.dropna(subset=['expiry_date'])
    
    # Vectorized time calc
    # result is Timedelta, .dt.total_seconds() works
    df['time_to_expiry_years'] = (df['expiry_date'] - now).dt.total_seconds() / (365.0 * 24.0 * 3600.0)
    
    # Filter out expired
    df = df[df['time_to_expiry_years'] > 0]
    
    # FORCE USE OF REAL SPOT PRICE (Index Price)
    # This prevents using Futures Price (Contango) for GEX calculation
    if real_spot is not None and real_spot > 0:
        df['underlying_price'] = float(real_spot)
    else:
        # Fallback (Old Logic)
        if 'index_price_summary' in df.columns:
            df['underlying_price'] = df['index_price_summary']
        elif 'index_price' in df.columns:
            df['underlying_price'] = df['index_price']
        
        # Fallback to underlying_price_summary if index_price missing
        if 'underlying_price' not in df.columns and 'underlying_price_summary' in df.columns:
            df['underlying_price'] = df['underlying_price_summary']
        
    return df
        
    return df
