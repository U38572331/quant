import sys
import os
import pandas as pd

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from src.analytics import MarketAnalyzer
    print("Import successful!")
    
    # Create dummy df
    df = pd.DataFrame({'underlying_price': [100], 'instrument_type': ['call'], 'strike': [100], 'time_to_expiry_years': [0.1]})
    analyzer = MarketAnalyzer(df)
    
    if hasattr(analyzer, 'filter_by_expiry'):
        print("Method 'filter_by_expiry' exists.")
        analyzer.filter_by_expiry(24)
        print("Method call successful.")
    else:
        print("Method 'filter_by_expiry' DOES NOT exist.")
        print(f"Available attributes: {dir(analyzer)}")

except Exception as e:
    print(f"Error: {e}")
