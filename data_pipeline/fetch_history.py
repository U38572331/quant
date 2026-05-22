import yfinance as yf
import pandas as pd
import os

# List of symbols identified from the image
symbols = ["MSCI", "BLK", "ARES", "CME", "KKR", "APO", "ICE", "BX"]

# Create a directory for the results
results_dir = "historical_data"
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

print(f"Fetching data for: {', '.join(symbols)}")

for symbol in symbols:
    print(f"Downloading {symbol}...")
    try:
        # Fetching last 20 years of daily data
        data = yf.download(symbol, period="20y", interval="1d")
        if not data.empty:
            file_path = os.path.join(results_dir, f"{symbol}_history.csv")
            data.to_csv(file_path)
            print(f"Saved {symbol} data to {file_path}")
        else:
            print(f"No data found for {symbol}")
    except Exception as e:
        print(f"Error downloading {symbol}: {e}")

print("Done!")
