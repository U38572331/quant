import yfinance as yf
import pandas as pd
import numpy as np
import itertools
import random

def calc_mdd_and_return(prices):
    """
    Calculate Cumulative Return and Maximum Drawdown from a price series.
    Returns: (cumulative_return, max_drawdown)
    """
    # Cumulative Return
    cum_ret = (prices.iloc[-1] / prices.iloc[0]) - 1

    # Max Drawdown
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    mdd = drawdown.min()
    
    return cum_ret, mdd

def calculate_portfolio_metrics(weighted_returns):
    """
    Given a series of daily portfolio returns, calculate cumulative return and MDD.
    """
    # Convert daily returns back to price series assuming start value of 1.0
    prices = (1 + weighted_returns).cumprod()
    return calc_mdd_and_return(prices)

def main():
    # Universe of large well-known ETFs across different sectors/asset classes
    tickers = [
        "SPY", "IVV", "VOO", "VTI", "QQQ", "VEA", "IEFA", "AGG", "BND", "VWO",
        "VUG", "IJH", "IEMG", "IWF", "IWM", "VTV", "IWD", "GLD", "VIG", "VNQ",
        "VXUS", "EFA", "XLF", "LQD", "QUAL", "VYM", "VGT", "BIV", "IJR", "ITOT",
        "VO", "XLK", "VSM", "IVW", "SCHD", "SPHD", "XLE", "IWN", "MTUM", "IGE",
        "XLV", "IWB", "SHV", "SCHX", "SCHB", "RSP", "SDY", "SPYV", "SPYG", "MDY",
        "VBR", "DIA", "XLU", "VB", "SCHF", "XLP", "XLY", "SLV", "EEM", "BIL",
        "XLB", "XLI", "MUB", "IEI", "SHY", "IEF", "TLT", "TIP", "MBB", "IGIB",
        "BNDX", "EMB", "HYG", "JNK", "SCHP", "BSV", "VCIT", "VCSH", "ANGL", "FALN",
        "GOVT", "TLH", "SPAB", "BKLN", "SRLN", "FLOT", "USIG", "IGSB", "IGHG", "SPLB",
        "VCLT", "VWOB", "IGTB", "FBND", "TOTL", "GVI", "NEAR", "MINT", "SOXX", "SMH",
        "IBB", "XBI", "KRE", "GDX", "URNM", "TQQQ", "UPRO", "SQQQ", "SH", "PSQ"
    ]
    
    # Clean duplicates & select unique
    tickers = list(set(tickers))

    print(f"Downloading data for {len(tickers)} ETFs (10 years)...")
    data = yf.download(tickers, start="2016-04-09", end="2026-04-09", group_by='ticker', auto_adjust=False)

    # Some versions of yfinance return MultiIndex differently depending on 'group_by'
    # Easier way to get adj close robustly
    data = yf.download(tickers, start="2016-04-09", end="2026-04-09")
    
    # Foolproof data extraction for 'Close' prices
    price_df = pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if 'Close' in data.columns.levels[0]:
            price_df = data['Close']
        else:
            for t in tickers:
                if t in data.columns.levels[0]:
                    try:
                        price_df[t] = data[t]['Close']
                    except:
                        pass
    else:
        price_df = data
    
    adj_close = price_df
        
    print(f"Initial shape of price data: {adj_close.shape}")
    
    # Filter for ETFs that have data starting near 2016-04-09 (must have >= 10 years history)
    # We allow some missing days initially but they must have valid data in the first 10 rows
    valid_tickers = []
    for ticker in adj_close.columns:
        # Check if the first 10 days have at least 1 non-NaN value (proxy for "existed 10 years ago")
        # Notice: If yfinance puts the column name as ticker, we use it directly.
        if not adj_close[ticker].iloc[:10].isna().all():
            valid_tickers.append(ticker)
            
    print(f"ETFs with >=10 years history: {len(valid_tickers)}")
    if 'SPY' not in valid_tickers:
        print("SPY failed the validation check! Check SPY head:")
        print(adj_close['SPY'].head(15))
    
    
    adj_close = adj_close[valid_tickers].dropna(axis=0, how='all') # Drop days where ALL are na
    adj_close = adj_close.ffill().bfill() # Fill the remaining NaNs for continuous series

    # Calculate SPY Baseline
    if "SPY" not in adj_close.columns:
        print("SPY data not available, exiting.")
        return

    spy_ret, spy_mdd = calc_mdd_and_return(adj_close["SPY"])
    print("==================================================")
    print(f"SPY Baseline (10 Years): Return = {spy_ret*100:.2f}%, Max Drawdown = {spy_mdd*100:.2f}%")
    print("==================================================")

    # Calculate individual ETF basic metrics
    results = []
    for ticker in valid_tickers:
        ret, mdd = calc_mdd_and_return(adj_close[ticker])
        results.append({
            "Portfolio": ticker,
            "Type": "Individual",
            "Return": ret,
            "MDD": mdd
        })
    
    # Convert to DataFrame to select individual assets that beat SPY
    df_results = pd.DataFrame(results)
    beats_spy = df_results[(df_results["Return"] > spy_ret) & (df_results["MDD"] > spy_mdd)]
    # Wait, MDD is negative (e.g. -0.30). "Smaller drawdown" means MDD absolute value is lower, i.e., MDD > spy_mdd
    
    print("\nIndividual ETFs beating SPY (Higher Return AND Smaller Drawdown):")
    if len(beats_spy) > 0:
        print(beats_spy.sort_values(by="Return", ascending=False).to_string(index=False))
    else:
        print("No individual ETF beat SPY on both metrics natively.")
    
    
    # Portfolio Generation (Combinations)
    print("\nGenerating equal-weighted Portfolio combinations...")
    daily_returns = adj_close.pct_change().dropna()
    
    # To avoid combinatorial explosion, let's take a subset of promising ETFs.
    # Mix of growth, broad market, bonds, gold, defensive.
    # We take anything with >0 return, diverse. Or just top 20 by return + top 10 low drawdown.
    top_ret_tickers = df_results.sort_values(by="Return", ascending=False).head(30)["Portfolio"].tolist()
    low_mdd_tickers = df_results.sort_values(by="MDD", ascending=False).head(20)["Portfolio"].tolist() # High MDD value means smaller drawdown (e.g., -0.05 > -0.30)
    
    combination_pool = list(set(top_ret_tickers + low_mdd_tickers))
    if "SPY" in combination_pool: combination_pool.remove("SPY")
    
    portfolios_to_test = []
    # Generate Pairs
    for pair in itertools.combinations(combination_pool, 2):
        portfolios_to_test.append(pair)
    # Generate Trios
    for trio in itertools.combinations(combination_pool, 3):
        portfolios_to_test.append(trio)
        
    print(f"Total combinations to test (Pairs & Trios): {len(portfolios_to_test)}")
    
    # Due to potentially large number of combinations, let's sample or just run them all.
    # If len(trios) is huge (e.g. 50C3 = 19600), we can process them fast via matrix operations.
    # Let's vectorize it.
    
    returns_matrix = daily_returns[combination_pool].values # shape (days, assets)
    asset_to_idx = {asset: i for i, asset in enumerate(combination_pool)}
    
    combo_results = []
    
    for combo in portfolios_to_test:
        indices = [asset_to_idx[asset] for asset in combo]
        # Equal weights
        weights = np.ones(len(indices)) / len(indices)
        
        # Portfolio daily returns = dot product of daily returns and weights
        combo_daily_returns = daily_returns_matrix_subset = returns_matrix[:, indices] @ weights
        
        # Calculate combination metrics
        # Cumulative return
        cum_ret = np.prod(1 + combo_daily_returns) - 1
        
        if cum_ret <= spy_ret: continue # Quick filter
        
        # Calculate MDD
        cum_prices = np.cumprod(1 + combo_daily_returns)
        roll_max = np.maximum.accumulate(cum_prices)
        drawdown = (cum_prices - roll_max) / roll_max
        mdd = np.min(drawdown)
        
        if mdd > spy_mdd: # MDD is negative, smaller drawdown -> strictly greater value
            combo_results.append({
                "Portfolio": " + ".join(combo),
                "Type": f"{len(combo)}-Asset Equal Weight",
                "Return": cum_ret,
                "MDD": mdd,
                "Return/MDD": cum_ret / abs(mdd)  # Simplified risk-adjusted return
            })
            
    df_combo = pd.DataFrame(combo_results)
    
    if len(df_combo) == 0:
        print("No combinations found beating SPY on both metrics.")
    else:
        # Sort by Return/MDD risk adjusted metric
        df_combo = df_combo.sort_values(by="Return", ascending=False) # Or sort by Return
        print(f"\nFound {len(df_combo)} combinations beating SPY. Top 20 by Return:")
        top_20 = df_combo.head(20).copy()
        top_20['Return'] = top_20['Return'].apply(lambda x: f"{x*100:.2f}%")
        top_20['MDD'] = top_20['MDD'].apply(lambda x: f"{x*100:.2f}%")
        top_20['Return/MDD'] = top_20['Return/MDD'].apply(lambda x: f"{x:.2f}")
        print(top_20.to_string(index=False))
        
        df_combo.to_csv("spy_beating_portfolios.csv", index=False)
        print("\nAll passing combinations saved to spy_beating_portfolios.csv")

if __name__ == "__main__":
    main()
