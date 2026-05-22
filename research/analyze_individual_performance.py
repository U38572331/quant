import pandas as pd
import yfinance as yf
import os
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
weights = {
    "MSCI": 0.15, "BLK": 0.15, "ARES": 0.15, "CME": 0.125,
    "KKR": 0.125, "APO": 0.10, "ICE": 0.10, "BX": 0.10
}
results_dir = "historical_data"
spx_tr_ticker = "^SP500TR"

print("Fetching S&P 500 Total Return data...")
spx_tr_data = yf.download(spx_tr_ticker, period="20y", interval="1d")
if isinstance(spx_tr_data.columns, pd.MultiIndex):
    spx_close = spx_tr_data[('Close', spx_tr_ticker)]
else:
    spx_close = spx_tr_data['Close']

all_returns_daily = {}

print("Calculating daily total returns for each ticker...")
for ticker in weights.keys():
    price_file = os.path.join(results_dir, f"{ticker}_history.csv")
    div_file = os.path.join(results_dir, f"{ticker}_dividends.csv")
    
    if os.path.exists(price_file):
        # Read price - handling potential different CSV headers from yfinance
        try:
            price_df = pd.read_csv(price_file, header=[0, 1], index_col=0, parse_dates=True)
            if ('Close', ticker) in price_df.columns:
                prices = price_df[('Close', ticker)]
            elif ('Price', 'Close') in price_df.columns:
                prices = price_df[('Price', 'Close')]
            else:
                 prices = price_df.iloc[:, 0]
        except:
            price_df = pd.read_csv(price_file, index_col=0, parse_dates=True)
            prices = price_df['Close'] if 'Close' in price_df.columns else price_df.iloc[:, 0]

        if os.path.exists(div_file):
            divs = pd.read_csv(div_file, index_col=0, parse_dates=True)
            df_combined = pd.DataFrame({'Price': prices})
            df_combined = df_combined.join(divs, how='left').fillna(0)
            # Daily Total Return = (P_t + D_t) / P_{t-1}
            returns = (df_combined['Price'] + df_combined.iloc[:, 1]) / df_combined['Price'].shift(1) - 1
            all_returns_daily[ticker] = returns
        else:
            all_returns_daily[ticker] = prices.pct_change()
    else:
        print(f"Warning: {price_file} not found.")

spx_returns_daily = spx_close.pct_change()
returns_df = pd.DataFrame(all_returns_daily)
returns_df['SPX_TR'] = spx_returns_daily
returns_df = returns_df.dropna()

# Calculate Annual Returns
years = sorted(returns_df.index.year.unique())
annual_results = []

for year in years:
    year_data = returns_df[returns_df.index.year == year]
    if year_data.empty: continue
    
    row = {"Year": year}
    for col in returns_df.columns:
        # Annualized return for the year
        ann_ret = (1 + year_data[col]).prod() - 1
        row[col] = round(ann_ret * 100, 2)
    annual_results.append(row)

annual_df = pd.DataFrame(annual_results)

# 1. Save Markdown Report
md_content = "# Individual Stock vs Market Annual Performance\n\n"
md_content += annual_df.to_markdown(index=False)
md_content += "\n\n> Note: Returns are Total Returns (including dividends) in percentage (%).\n"

with open("individual_performance_report.md", "w", encoding='utf-8') as f:
    f.write(md_content)

# 2. Generate Interactive Dashboard
fig = go.Figure()

for ticker in weights.keys():
    fig.add_trace(go.Bar(
        x=annual_df['Year'],
        y=annual_df[ticker],
        name=ticker,
        visible='legendonly' if ticker not in ["MSCI", "BLK", "BX"] else True
    ))

fig.add_trace(go.Bar(
    x=annual_df['Year'],
    y=annual_df['SPX_TR'],
    name="S&P 500 TR",
    marker_color='rgba(255, 255, 255, 0.8)',
    marker_line_color='white',
    marker_line_width=1.5
))

fig.update_layout(
    title="Annual Performance Comparison: Portfolio Tickers vs S&P 500",
    xaxis_title="Year",
    yaxis_title="Annual Return (%)",
    template="plotly_dark",
    barmode='group',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=50, r=50, t=100, b=50),
    height=700
)

html_path = "individual_analysis.html"
fig.write_html(html_path)

print(f"Report saved to individual_performance_report.md")
print(f"Dashboard saved to {html_path}")
