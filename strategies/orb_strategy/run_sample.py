import os
import sys
import time
import pandas as pd
from datetime import datetime

# Local module imports
from orb_rv_strategy import ORBRelativeVolumeStrategy
from av_fetcher import AlphaVantageFetcher

# Set the AV key directly
API_KEY = "FPO35TPP2ALAJ4C1"

def main():
    fetcher = AlphaVantageFetcher(api_key=API_KEY)
    strategy = ORBRelativeVolumeStrategy()
    
    # Due to API limits, we will test on a few highly liquid Nasdaq stocks.
    test_symbols = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT"]
    
    daily_data_dict = {}
    intraday_data_dict = {}
    
    print(f"Fetching data for symbols: {test_symbols}")
    
    for symbol in test_symbols:
        print(f"Fetching {symbol} daily data...")
        daily_df = fetcher.fetch_daily_data(symbol)
        
        print(f"Fetching {symbol} intraday data...")
        intra_df = fetcher.fetch_intraday_data(symbol, '5min')
        
        # Simple sleep to avoid AV standard rate limits (5 per min on free tiers usually, 
        # though standard keys might have higher limits, better safe than sorry)
        time.sleep(2)
        
        if not daily_df.empty and not intra_df.empty:
            # Add features required by the strategy
            daily_data_dict[symbol] = strategy.calculate_daily_indicators(daily_df)
            intraday_data_dict[symbol] = strategy.calculate_first_5min_volume(intra_df)
        else:
            print(f"[!] Warning: Missing data for {symbol}.")
            
    print("-" * 50)
    print("Evaluating recent ORB signals based on strategy rules (Relative Volume)...")
    
    # We evaluate for the most recent common date.
    if len(intraday_data_dict) == 0:
        print("No valid intraday data was fetched. Exiting.")
        return
        
    # Get the last available intraday date from the first successfully fetched symbol
    sample_symbol = list(intraday_data_dict.keys())[0]
    dates_available = intraday_data_dict[sample_symbol].index
    
    print(f"\nRecent Dates available for Relative Volume: {[str(d) for d in dates_available[-3:]]}")
    
    # Evaluate for the last 3 trading days
    for test_date in dates_available[-3:]:
        print(f"\n[ Candidates for {test_date} ]")
        candidates = strategy.select_top_candidates(
            current_date=test_date,
            daily_data_dict=daily_data_dict,
            intraday_data_dict=intraday_data_dict
        )
        
        if not candidates:
            print("  No stocks met the ORB Relative Volume strategy criteria on this day.")
        
        for i, c in enumerate(candidates):
            print(f"  #{i+1} {c['ticker']:<5} | RelVol: {c['rel_vol']:.2f}x | ATR: ${c['atr']:.2f} | Open: ${c['open']:.2f}")

if __name__ == "__main__":
    main()
