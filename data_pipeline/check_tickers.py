import yfinance as yf
import pandas as pd

groups = {
    "Rule Makers": ["MSCI", "SPGI", "MCO", "CME", "ICE"],
    "Network Effects": ["V", "MA", "META", "GOOGL", "TCEHY"],
    "AI & Infrastructure": ["MSFT", "AMZN", "NVDA", "TSM", "ASML", "AVGO"],
    "Information Control": ["RELX", "TRI", "IQV"],
    "Physical Infrastructure": ["UNP", "CSX", "NEE", "WM", "XOM"]
}

all_tickers = [t for g in groups.values() for t in g] + ["SPY"]

def check_history():
    data = yf.download(all_tickers, start="2014-01-01", end="2025-01-01")
    # For newer yfinance versions, Adj Close might be under a MultiIndex level 0
    if 'Adj Close' in data.columns.levels[0]:
        adj_close = data['Adj Close']
    elif 'Close' in data.columns.levels[0]:
        adj_close = data['Close']
    else:
        print("Columns found:", data.columns)
        return

    print(adj_close.info())
    print("\nMissing values per ticker:")
    print(adj_close.isnull().sum())
    print("\nEarliest non-null date per ticker:")
    for ticker in all_tickers:
        valid_data = adj_close[ticker].dropna()
        first_date = valid_data.index[0] if not valid_data.empty else "No Data"
        print(f"{ticker}: {first_date}")

if __name__ == "__main__":
    check_history()
