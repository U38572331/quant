import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configuration: Tickers and Weights
weights = {
    "MSCI": 0.15,
    "BLK": 0.15,
    "ARES": 0.15,
    "CME": 0.125,
    "KKR": 0.125,
    "APO": 0.10,
    "ICE": 0.10,
    "BX": 0.10
}

results_dir = "historical_data"
spx_ticker = "^GSPC"

print("Fetching SPX data...")
spx_data = yf.download(spx_ticker, period="20y", interval="1d")['Close']

all_data = {}
for ticker in weights.keys():
    file_path = os.path.join(results_dir, f"{ticker}_history.csv")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        # Correctly handle 2-level headers from yfinance output
        df = pd.read_csv(file_path, header=[0, 1], index_col=0, parse_dates=True)
        # The first column group is usually 'Close' under the ticker name
        if ('Close', ticker) in df.columns:
            all_data[ticker] = df[('Close', ticker)]
        elif ('Price', 'Close') in df.columns: # Sometimes yfinance adds a 'Price' level
             all_data[ticker] = df[('Price', 'Close')]
        else:
            # Fallback for version differences
            print(f"Columns for {ticker}: {df.columns}")
            all_data[ticker] = df.iloc[:, 0] # Assume Close is the first column
    else:
        print(f"Warning: {file_path} not found.")

# Combine data
portfolio_df = pd.DataFrame(all_data)
# Add SPX
portfolio_df['SPX'] = spx_data

# Drop rows where any data is missing to find the common period
portfolio_df = portfolio_df.dropna()
earliest_date = portfolio_df.index.min()
print(f"Common period starts from: {earliest_date}")

# Calculate daily returns
returns_df = portfolio_df.pct_change().dropna()

# Calculate weighted portfolio return
returns_df['Portfolio'] = sum(returns_df[ticker] * weight for ticker, weight in weights.items())

# Calculate cumulative returns
cumulative_returns = (1 + returns_df[['Portfolio', 'SPX']]).cumprod() * 100
# Add starting point (100)
start_row = pd.DataFrame([[100, 100]], columns=['Portfolio', 'SPX'], index=[earliest_date])
cumulative_returns = pd.concat([start_row, cumulative_returns])

# Plotting
plt.figure(figsize=(12, 7))
sns.set_style("darkgrid")
plt.plot(cumulative_returns.index, cumulative_returns['Portfolio'], label='Financial Portfolio (Weighted)', linewidth=2.5, color='#1f77b4')
plt.plot(cumulative_returns.index, cumulative_returns['SPX'], label='S&P 500 (SPX)', linewidth=2, color='#ff7f0e', linestyle='--')

plt.title('Portfolio vs S&P 500 Cumulative Performance', fontsize=16)
plt.ylabel('Cumulative Return (Base 100)', fontsize=12)
plt.xlabel('Date', fontsize=12)
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)

# Save result
output_file = "portfolio_vs_spx.png"
plt.savefig(output_file)
print(f"Comparison chart saved to {output_file}")
