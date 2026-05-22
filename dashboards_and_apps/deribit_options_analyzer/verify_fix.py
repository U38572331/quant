
import pandas as pd
from src.client import DeribitClient
from src.utils import enrich_data
from src.analytics import MarketAnalyzer

def verify():
    print("Fetching data...")
    client = DeribitClient()
    instruments = client.get_instruments("BTC")
    summary = client.get_book_summary_by_currency("BTC")
    
    if instruments.empty or summary.empty:
        print("Failed to fetch data.")
        return

    df = enrich_data(instruments, summary)
    analyzer = MarketAnalyzer(df)
    
    print("\n--- Testing get_major_expiry ---")
    
    # Week
    week_exp = analyzer.get_major_expiry('week')
    print(f"Week Expiry Identified: {week_exp}")
    if week_exp:
        sub = MarketAnalyzer(df[df['expiry_date'] == week_exp])
        print(f"Week Max Pain: {sub.calculate_max_pain()}")
        
    # Month
    month_exp = analyzer.get_major_expiry('month')
    print(f"Month Expiry Identified: {month_exp}")
    if month_exp:
        sub = MarketAnalyzer(df[df['expiry_date'] == month_exp])
        print(f"Month Max Pain: {sub.calculate_max_pain()}")

    # Quarter
    quarter_exp = analyzer.get_major_expiry('quarter')
    print(f"Quarter Expiry Identified: {quarter_exp}")
    if quarter_exp:
        sub = MarketAnalyzer(df[df['expiry_date'] == quarter_exp])
        mp = sub.calculate_max_pain()
        print(f"Quarter Max Pain: {mp}")
        if mp > 90000:
            print("SUCCESS: Quarter Max Pain is > 90000 (likely 96k/100k), confirming it's using the specific contract.")
        else:
            print("WARNING: Quarter Max Pain is low. Check if it matches aggregated value.")

if __name__ == "__main__":
    verify()
