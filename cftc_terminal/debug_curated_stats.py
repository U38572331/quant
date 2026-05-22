import sqlite3
import pandas as pd

CURATED_LIST = {
    'S&P 500': ['E-MINI S&P 500', 'S&P 500 CONSOLIDATED'],
    'Nasdaq 100': ['NASDAQ-100', 'E-MINI NASDAQ-100', 'NASDAQ-100 CONSOLIDATED'],
    'Dow Jones': ['DOW JONES', 'DJIA CONSOLIDATED'],
    'VIX': ['VIX', 'CBOE VOLATILITY INDEX'],
    'Nikkei 225': ['NIKKEI'],
    'Gold': ['GOLD', 'MICRO GOLD'],
    'Silver': ['SILVER'],
    'Copper': ['COPPER'],
    'Crude Oil (WTI)': ['CRUDE OIL', 'WTI', 'LIGHT SWEET CRUDE OIL'],
    'Natural Gas': ['NATURAL GAS', 'HENRY HUB'],
    'Bitcoin': ['BITCOIN'],
    'Ether': ['ETHER', 'ETHEREUM'],
    'EUR/USD': ['EURO FX', 'EURO'],
    'JPY/USD': ['JAPANESE YEN'],
    'GBP/USD': ['BRITISH POUND'],
    'Corn': ['CORN'],
    'Soybeans': ['SOYBEANS'],
    'Wheat': ['WHEAT']
}

try:
    conn = sqlite3.connect("cftc_data.db")
    cursor = conn.cursor()
    
    # Get all markets to simulate matching
    all_markets = pd.read_sql("SELECT DISTINCT market_and_exchange_names, cftc_contract_market_code FROM cot_legacy", conn)
    
    print(f"{'DISPLAY NAME':<20} | {'MATCHED NAME':<30} | {'CODE':<10} | {'ROWS'}")
    print("-" * 75)
    
    for display_key, keywords in CURATED_LIST.items():
        # Simulate app logic matching
        match = None
        for k in keywords:
            found = all_markets[all_markets['market_and_exchange_names'].str.upper().str.contains(k)]
            if not found.empty:
                # In app we take first, here we take first too
                match = found.iloc[0]
                break
        
        if match is not None:
            # Check row count
            count = cursor.execute("SELECT COUNT(*) FROM cot_legacy WHERE cftc_contract_market_code = ?", (match['cftc_contract_market_code'],)).fetchone()[0]
            print(f"{display_key:<20} | {match['market_and_exchange_names'][:30]:<30} | {match['cftc_contract_market_code']:<10} | {count}")
        else:
            print(f"{display_key:<20} | {'-- NOT FOUND --':<30} | {'--'} | 0")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
