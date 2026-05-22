import pandas as pd
import yfinance as yf
import os
import json

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
spx_tr_ticker = "^SP500TR" # S&P 500 Total Return Index
starting_capital = 1000000

print("Fetching S&P 500 Total Return (SPX-TR) data...")
spx_tr_data = yf.download(spx_tr_ticker, period="20y", interval="1d")

# Note: yfinance 0.2.x+ returns multi-index
if isinstance(spx_tr_data.columns, pd.MultiIndex):
    spx_close = spx_tr_data[('Close', spx_tr_ticker)]
else:
    spx_close = spx_tr_data['Close']

all_returns = {}

for ticker in weights.keys():
    price_file = os.path.join(results_dir, f"{ticker}_history.csv")
    div_file = os.path.join(results_dir, f"{ticker}_dividends.csv")
    
    if os.path.exists(price_file):
        # Read price
        price_df = pd.read_csv(price_file, header=[0, 1], index_col=0, parse_dates=True)
        if ('Close', ticker) in price_df.columns:
            prices = price_df[('Close', ticker)]
        elif ('Price', 'Close') in price_df.columns:
            prices = price_df[('Price', 'Close')]
        else:
             prices = price_df.iloc[:, 0]
             
        # Read dividends
        if os.path.exists(div_file):
            divs = pd.read_csv(div_file, index_col=0, parse_dates=True)
            # Alignment: Add dividends to the specific dates they occurred
            # For total return calculation: Daily Return = (P_t + D_t) / P_{t-1}
            # We combine them by reindexing dividends to price dates
            df_combined = pd.DataFrame({'Price': prices})
            df_combined = df_combined.join(divs, how='left').fillna(0)
            # Daily Total Return
            returns = (df_combined['Price'] + df_combined.iloc[:, 1]) / df_combined['Price'].shift(1)
            all_returns[ticker] = returns - 1
        else:
            all_returns[ticker] = prices.pct_change()
    else:
        print(f"Warning: {price_file} not found.")

# Process SPX-TR return
spx_returns = spx_close.pct_change()

# Combine all returns
returns_df = pd.DataFrame(all_returns)
returns_df['SPX_TR'] = spx_returns

# Common period
returns_df = returns_df.dropna()
earliest_date = returns_df.index.min()
print(f"Calculation starts from: {earliest_date}")

# Calculate weighted portfolio return
returns_df['Portfolio'] = sum(returns_df[ticker] * weight for ticker, weight in weights.items())

# Calculate Capital paths (Lump Sum)
capital_paths = (1 + returns_df[['Portfolio', 'SPX_TR']]).cumprod() * starting_capital

# Calculate DCA paths (1M Initial + 1k Monthly)
# We'll do this iteratively to account for contributions
dca_amount = 1000
portfolio_dca = [starting_capital]
spx_dca = [starting_capital]

current_month = earliest_date.month

for i in range(len(returns_df)):
    date = returns_df.index[i]
    ret_p = returns_df['Portfolio'].iloc[i]
    ret_s = returns_df['SPX_TR'].iloc[i]
    
    # Apply return
    p_val = portfolio_dca[-1] * (1 + ret_p)
    s_val = spx_dca[-1] * (1 + ret_s)
    
    # Add contribution if new month
    if date.month != current_month:
        p_val += dca_amount
        s_val += dca_amount
        current_month = date.month
        
    portfolio_dca.append(p_val)
    spx_dca.append(s_val)

# Add starting point for Lump Sum
start_data = pd.DataFrame([[starting_capital, starting_capital]], columns=['Portfolio', 'SPX_TR'], index=[earliest_date - pd.Timedelta(days=1)])
capital_paths = pd.concat([start_data, capital_paths])

# Calculate Annual Returns (Jan to Dec)
annual_returns = []
years = returns_df.index.year.unique()

for year in years:
    year_data = returns_df[returns_df.index.year == year]
    if year_data.empty:
        continue
    
    # Simple cumulative return for the year: (1 + r1)*(1 + r2)*... - 1
    p_ann = (1 + year_data['Portfolio']).prod() - 1
    s_ann = (1 + year_data['SPX_TR']).prod() - 1
    
    annual_returns.append({
        "year": int(year),
        "portfolio": round(p_ann * 100, 2), # in percentage
        "spx": round(s_ann * 100, 2)     # in percentage
    })

# Prepare JSON data for web visualization
json_data = {
    "dates": capital_paths.index.strftime('%Y-%m-%d').tolist(),
    "lump_sum": {
        "portfolio": capital_paths['Portfolio'].round(2).tolist(),
        "spx": capital_paths['SPX_TR'].round(2).tolist()
    },
    "dca": {
        "portfolio": [round(v, 2) for v in portfolio_dca],
        "spx": [round(v, 2) for v in spx_dca]
    },
    "annual": annual_returns
}

with open("capital_data.json", "w") as f:
    json.dump(json_data, f)

print("Capital data saved to capital_data.json with annual returns.")

print("Capital data path saved to capital_data.json")
