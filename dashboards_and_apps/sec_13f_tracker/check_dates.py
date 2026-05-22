import pandas as pd

try:
    df = pd.read_csv('latest_13f_holdings.csv')
    with open('dates_summary.txt', 'w') as f:
        f.write("Unique Filing Dates per Fund:\n")
        summary = df.groupby(['Fund', 'FilingDate']).size().reset_index(name='HoldingsCount')
        summary.sort_values('FilingDate', inplace=True)
        f.write(summary.to_string())
        
except Exception as e:
    with open('dates_summary.txt', 'w') as f:
        f.write(str(e))
