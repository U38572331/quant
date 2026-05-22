import pandas as pd

try:
    df = pd.read_csv('latest_13f_holdings.csv')
    # Filter for older dates
    old_filings = df[df['FilingDate'].str.contains('2016')]
    if not old_filings.empty:
        print("Found old filings:")
        print(old_filings[['Fund', 'FilingDate', 'CIK']].drop_duplicates().to_string())
    else:
        print("No filings from 2016 found.")
        
    # Also just print unique dates again, but cleaner
    print("\nDate Summary:")
    print(df.groupby(['Fund', 'FilingDate']).size().reset_index()[['Fund', 'FilingDate']].to_string())

except Exception as e:
    print(e)
