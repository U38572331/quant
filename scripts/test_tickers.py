import yfinance as yf

tickers = ["VOO", "QQQ", "SMH", "SCHD", "VIG", "VTG", "VYM", "VTI", "VT", "VGT", "VUG"]

for ticker in tickers:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        print(f"{ticker}: {info.get('shortName', 'No shortName')}")
        # Fetch 1 month data
        h = t.history(period="1mo")
        print(f"  Data count: {len(h)}")
    except Exception as e:
        print(f"{ticker} failed: {e}")
