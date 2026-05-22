import pandas as pd
import numpy as np
import scipy.optimize as sco
import os

# Configuration
weights_eq = np.array([0.10] * 10)
tickers = ["BX", "KKR", "APO", "ARES", "MSCI", "SPGI", "BLK", "CME", "CBOE", "NDAQ"]
results_dir = "historical_data"
spx_tr_ticker = "^SP500TR"
risk_free_rate = 0.04 # 4%
rf_daily = risk_free_rate / 252

import yfinance as yf

# Load SPX TR
spx_df = yf.download(spx_tr_ticker, period="15y", interval="1d")
spx_close = spx_df[('Close', '^SP500TR')] if isinstance(spx_df.columns, pd.MultiIndex) else spx_df['Close']
spx_returns = pd.to_numeric(spx_close, errors='coerce').pct_change()
spx_returns.index = pd.to_datetime(spx_returns.index).normalize()

all_returns = {}
for ticker in tickers:
    price_file = os.path.join(results_dir, f"{ticker}_history.csv")
    div_file = os.path.join(results_dir, f"{ticker}_dividends.csv")
    
    # Read price
    try:
        price_df = pd.read_csv(price_file, header=[0, 1], index_col=0, parse_dates=True)
        prices = price_df[('Close', ticker)] if ('Close', ticker) in price_df.columns else price_df.iloc[:, 0]
    except:
        price_df = pd.read_csv(price_file, index_col=0, parse_dates=True)
        prices = price_df['Close'] if 'Close' in price_df.columns else price_df.iloc[:, 0]
    
    # Handle dividends
    if os.path.exists(div_file):
        divs = pd.read_csv(div_file, index_col=0, parse_dates=True)
        divs.index = pd.to_datetime(divs.index, utc=True).tz_localize(None).normalize()
        prices.index = pd.to_datetime(prices.index).normalize()
        df_c = pd.DataFrame({'Price': pd.to_numeric(prices, errors='coerce')})
        df_c = df_c.join(pd.to_numeric(divs.iloc[:, 0], errors='coerce'), how='left').fillna(0)
        ret = (df_c['Price'] + df_c.iloc[:, 1]) / df_c['Price'].shift(1) - 1
        all_returns[ticker] = ret
    else:
        all_returns[ticker] = pd.to_numeric(prices, errors='coerce').pct_change()

returns_df = pd.DataFrame(all_returns)
returns_df['SPX_TR'] = spx_returns
returns_df = returns_df.dropna()

# Portfolio daily returns (equal initially)
returns_df['Portfolio'] = returns_df[tickers].dot(weights_eq)

port_ret = returns_df['Portfolio']
spx_ret = returns_df['SPX_TR']

# 1. Sharpe Ratio
ann_ret_port = (1 + port_ret).prod() ** (252 / len(port_ret)) - 1
vol_port = port_ret.std() * np.sqrt(252)
sharpe_ratio = (ann_ret_port - risk_free_rate) / vol_port

# 2. Sortino Ratio
target_return = 0
downside_returns = port_ret[port_ret < target_return]
downside_vol = downside_returns.std() * np.sqrt(252)
sortino_ratio = (ann_ret_port - risk_free_rate) / downside_vol

# 3. Information Ratio
active_return = port_ret - spx_ret
ann_active_ret = (1 + active_return).prod() ** (252 / len(active_return)) - 1
tracking_error = active_return.std() * np.sqrt(252)
info_ratio = ann_active_ret / tracking_error

# 4. CAPM (Beta & Alpha)
cov_matrix = returns_df[['Portfolio', 'SPX_TR']].cov() * 252
beta = cov_matrix.iloc[0, 1] / cov_matrix.iloc[1, 1]
ann_ret_spx = (1 + spx_ret).prod() ** (252 / len(spx_ret)) - 1
capm_expected_return = risk_free_rate + beta * (ann_ret_spx - risk_free_rate)
alpha = ann_ret_port - capm_expected_return

# 5. Kelly Criterion
# Full Kelly = Expected Excess Return / Variance
kelly_fraction = (ann_ret_port - risk_free_rate) / (vol_port ** 2)
half_kelly = kelly_fraction / 2

# 6. Risk Parity (Inverse Volatility approach as proxy for long-only unlevered ERC)
ann_vols = returns_df[tickers].std() * np.sqrt(252)
inv_vols = 1 / ann_vols
risk_parity_weights = inv_vols / inv_vols.sum()
rp_ann_ret = (1 + returns_df[tickers].dot(risk_parity_weights)).prod() ** (252 / len(port_ret)) - 1

# 7. Black-Litterman (Implied Equilibrium Returns)
# Pi = lambda * Sigma * W_mkt
# Let lambda = (Market Return - Risk Free Rate) / Market Variance
mkt_vol = spx_ret.std() * np.sqrt(252)
risk_aversion = (ann_ret_spx - risk_free_rate) / (mkt_vol ** 2)
cov_assets = returns_df[tickers].cov() * 252
implied_returns = risk_aversion * cov_assets.dot(weights_eq)

# Prepare Markdown Report
md = f"""# 15-Year Quantitative Portfolio Evaluation Report

This report evaluates the equally-weighted 10-ticker portfolio against standard and advanced quantitative finance models, utilizing a 15-year daily total return history (assuming a {risk_free_rate*100}% Risk-Free Rate).

## 1. Core Risk-Adjusted Metrics

| Metric | Portfolio Value | Interpretation |
|---|---|---|
| **Annualized Return (CAGR)** | {ann_ret_port*100:.2f}% | Market (SPX) is {ann_ret_spx*100:.2f}% |
| **Annualized Volatility** | {vol_port*100:.2f}% | Expected variance in portfolio value. |
| **Sharpe Ratio** | {sharpe_ratio:.2f} | Excess return per unit of total volatility. > 1 indicates excellent risk-adjusted performance. |
| **Sortino Ratio** | {sortino_ratio:.2f} | Return relative to **downside** risk only. Punishes only losing volatility. |
| **Information Ratio (IR)** | {info_ratio:.2f} | Consistency in beating the benchmark (SPX). Tracking Error: {tracking_error*100:.2f}%. |

## 2. Capital Asset Pricing Model (CAPM)
CAPM decomposes returns into systemic market risk (Beta) and manager skill (Alpha).

- **Portfolio Beta (β):** {beta:.2f}
  *The portfolio is {"more" if beta > 1 else "less"} volatile than the broader market.*
- **CAPM Expected Return:** {capm_expected_return*100:.2f}%
- **Jensen's Alpha (α):** {alpha*100:.2f}%
  *The portfolio generated an annualized excess return of {alpha*100:.2f}% above what CAPM predicted.*

## 3. Kelly Criterion (Optimal Leverage/Position Sizing)
The Kelly equation outputs the theoretical fraction of your bankroll to allocate to this strategy to maximize compound growth over the long term.

- **Full Kelly Fraction:** {kelly_fraction*100:.2f}%
- **Half Kelly (Recommended for safety):** {half_kelly*100:.2f}%
> *Note: A Kelly fraction > 100% implies the theoretical mathematics suggest applying leverage. In practice, conservative sizing (like Half-Kelly) is strongly advised due to non-normal return distributions ("fat tails").*

## 4. Risk Parity (Risk Contribution Equalization)
Currently, your portfolio is **10% Equal Weighted** by capital. However, higher-volatility stocks contribute more to the actual portfolio risk. A simplified **Risk Parity** approach (Inverse Volatility Weighted) would equalize the risk distribution:

| Ticker | Equal Weight | Risk Parity Weight (Suggested) | Annualized Volatility |
|---|---|---|---|
"""

for tick, rp_w, vol in zip(tickers, risk_parity_weights, ann_vols):
    md += f"| {tick} | 10.00% | {rp_w*100:.2f}% | {vol*100:.2f}% |\n"

md += f"\n*Applying Risk Parity weights historically would have yielded a CAGR of {rp_ann_ret*100:.2f}%.*\n\n"

md += f"""## 5. Black-Litterman Model (Implied Equilibrium Returns)
The Black-Litterman model begins by reverse-engineering the market's expectations. Assuming the current 10% equal weight represents the absolute "market equilibrium", what return must the market theoretically be expecting from each asset?

*(Calculated using Implied Aversion $\lambda$ = {risk_aversion:.2f})*

| Ticker | BL Implied Expected Return (Equilibrium) |
|---|---|
"""
for tick, imp_ret in zip(tickers, implied_returns):
    md += f"| {tick} | {imp_ret*100:.2f}% |\n"

md += "\n> **Actionable View:** Compare these implied expected returns to your personal forecasts. If you believe a stock will outperform its BL Implied Return, the Black-Litterman model dictates you should **overweight** it relative to 10%.\n"

with open(r"C:\Users\user\.gemini\antigravity\brain\94b3c258-68ae-4021-b830-56f62b4e8864\quant_evaluation_report.md", "w", encoding='utf-8') as f:
    f.write(md)

print("Quantitative evaluation report generated.")
