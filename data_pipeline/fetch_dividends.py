import yfinance as yf
import pandas as pd
import os

# List of symbols identified from the image
symbols = ["MSCI", "BLK", "ARES", "CME", "KKR", "APO", "ICE", "BX"]

# Create a directory for the results
results_dir = "historical_data"
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

print(f"Fetching dividend data for: {', '.join(symbols)}")

dividend_summary = []

for symbol in symbols:
    print(f"Downloading dividends for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        divs = ticker.dividends
        if not divs.empty:
            file_path = os.path.join(results_dir, f"{symbol}_dividends.csv")
            divs.to_csv(file_path)
            
            # Get last 5 years average annual dividends for summary
            last_year_div = divs.resample('YE').sum().iloc[-1] if not divs.empty else 0
            dividend_summary.append({
                "Ticker": symbol,
                "Last Annual Div": round(last_year_div, 4),
                "Latest Div Date": divs.index[-1].strftime('%Y-%m-%d')
            })
            print(f"Saved {symbol} dividends to {file_path}")
        else:
            print(f"No dividend data found for {symbol}")
    except Exception as e:
        print(f"Error downloading dividends for {symbol}: {e}")

# Save summary
if dividend_summary:
    summary_df = pd.DataFrame(dividend_summary)
    summary_df.to_csv(os.path.join(results_dir, "dividend_summary.csv"), index=False)
    print("Dividend summary saved.")

print("Done!")
