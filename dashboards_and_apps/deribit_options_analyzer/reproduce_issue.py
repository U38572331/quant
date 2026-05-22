
import pandas as pd
from src.client import DeribitClient
from src.utils import enrich_data
from src.analytics import MarketAnalyzer
import datetime

def run_investigation():
    print("Fetching data...")
    client = DeribitClient()
    instruments = client.get_instruments("BTC")
    summary = client.get_book_summary_by_currency("BTC")
    
    if instruments.empty or summary.empty:
        print("Failed to fetch data.")
        return

    df = enrich_data(instruments, summary)
    print(f"Total options: {len(df)}")
    
    # Analyze by Expiry Date
    expiries = sorted(df['expiry_date'].unique())
    print("\n--- Max Pain by Specific Expiry ---")
    for expiry in expiries:
        # Filter for this specific expiry
        expiry_df = df[df['expiry_date'] == expiry]
        analyzer = MarketAnalyzer(expiry_df)
        mp = analyzer.calculate_max_pain()
        
        # Calculate days to expiry
        days_to_expiry = (expiry - datetime.datetime.now()).days
        print(f"Expiry: {expiry.date()} (Days: {days_to_expiry}) | Options: {len(expiry_df)} | Max Pain: {mp}")

    # Analyze by "Quarterly" Logic (< 90 Days)
    print("\n--- Max Pain by App Logic (Aggregated) ---")
    
    analyzer_main = MarketAnalyzer(df)
    
    # 0DTE
    analyzer_0dte = analyzer_main.filter_by_expiry(hours=24, mode='under')
    pam_0dte = analyzer_0dte.calculate_max_pain()
    print(f"0DTE (<24h) Max Pain: {pam_0dte}")
    
    # Week
    analyzer_week = analyzer_main.filter_by_expiry(hours=24*7, mode='under')
    pam_week = analyzer_week.calculate_max_pain()
    print(f"Week (<7d) Max Pain: {pam_week}")
    
    # Month
    analyzer_month = analyzer_main.filter_by_expiry(hours=24*30, mode='under')
    pam_month = analyzer_month.calculate_max_pain()
    print(f"Month (<30d) Max Pain: {pam_month}")
    
    # Quarter
    analyzer_quarter = analyzer_main.filter_by_expiry(hours=24*90, mode='under')
    pam_quarter = analyzer_quarter.calculate_max_pain()
    print(f"Quarter (<90d) Max Pain: {pam_quarter}")
    
    # Check if there is a specific expiry around 90 days that differs
    print("\n--- Identifying 'Quarterly' Candidate ---")
    # Usually the one with largest OI in the 60-120 day range?
    # Or just the next major quarterly expiry.
    # Current date: Dec 2025. Next quarters: Mar 2026, Jun 2026.
    
    for expiry in expiries:
        days = (expiry - datetime.datetime.now()).days
        if 60 < days < 120:
             expiry_df = df[df['expiry_date'] == expiry]
             analyzer = MarketAnalyzer(expiry_df)
             mp = analyzer.calculate_max_pain()
             print(f"Candidate Quarterly: {expiry.date()} | Max Pain: {mp}")

if __name__ == "__main__":
    run_investigation()
