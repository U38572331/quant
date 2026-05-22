import yfinance as yf
import pandas as pd
import os

symbols = ["SPGI", "CBOE", "NDAQ"]
results_dir = "historical_data"
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

print(f"Fetching 15y history and dividends for: {', '.join(symbols)}")

dividend_summary = []

for symbol in symbols:
    print(f"Downloading {symbol} history...")
    try:
        data = yf.download(symbol, period="15y", interval="1d")
        if not data.empty:
            file_path = os.path.join(results_dir, f"{symbol}_history.csv")
            data.to_csv(file_path)
            print(f"Saved {symbol} data to {file_path}")
    except Exception as e:
        print(f"Error downloading {symbol}: {e}")

    print(f"Downloading {symbol} dividends...")
    try:
        ticker = yf.Ticker(symbol)
        divs = ticker.dividends
        if not divs.empty:
            file_path = os.path.join(results_dir, f"{symbol}_dividends.csv")
            divs.to_csv(file_path)
            last_year_div = divs.resample('YE').sum().iloc[-1] if not divs.empty else 0
            dividend_summary.append({
                "Ticker": symbol,
                "Last Annual Div": round(last_year_div, 4),
                "Latest Div Date": divs.index[-1].strftime('%Y-%m-%d')
            })
            print(f"Saved {symbol} dividends to {file_path}")
    except Exception as e:
        print(f"Error downloading dividends for {symbol}: {e}")

if dividend_summary:
    summary_df = pd.DataFrame(dividend_summary)
    summary_df.to_csv(os.path.join(results_dir, "dividend_summary_new.csv"), index=False)

print("Done!")
