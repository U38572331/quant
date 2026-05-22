import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

def get_etf_list():
    # Provide a comprehensive list of ~250 large globally known ETFs
    return list(set([
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
        "IBB", "XBI", "KRE", "GDX", "URNM", "TQQQ", "UPRO", "SQQQ", "SH", "PSQ",
        "ARKK", "ARKG", "ARKW", "ARKF", "ARKQ", "JEPI", "JEPQ", "DGRO", "DFAU", "VXF",
        "BNDW", "VT", "VTIP", "BOND", "MHI", "PTY", "PDI", "PCEF", "PGX", "PFF",
        "IYR", "SCHH", "XLRE", "USRT", "REM", "REZ", "FREL", "VNQI", "RWX", "RWR",
        "NOBL", "REGL", "KIE", "KBE", "IAI", "IYG", "VFH", "KCE", "FXI", "MCHI",
        "KWEB", "CQQQ", "ASHR", "GXC", "INDA", "EPI", "INDY", "SMIN", "EWG", "EWU",
        "EWJ", "EWC", "EWW", "EWA", "EWT", "EWY", "EWS", "EZA", "ECH", "EPU",
        "EPHE", "EIDO", "ENZL", "VNM", "FM", "XME", "COPX", "PICK", "REMX", "LIT",
        "URA", "BHP", "NLR", "CRAK", "TAN", "ICLN", "PBW", "QCLN", "FAN", "PBD",
        "BOTZ", "ROBO", "IRBO", "CIBR", "HACK", "BUG", "IHAK", "SKYY", "CLOU", "WCLD",
        "IGV", "XNTK", "SOXQ", "FTXL", "PSJ", "PNQI", "FDN", "KBE", "KRE", "KIE",
        "IAT", "IYG", "XLF", "VFH", "IYF", "UYG", "XHB", "ITB", "PKB", "MOO",
        "COWZ", "CALF", "PVAL", "SYLD", "SVAL", "AVUV", "AVDV", "AVEM", "AVUS",
        "DFAT", "DFAS", "DFAC", "DFAU", "DFUS", "DFEV", "DFIV", "DFIS", "DFIC"
    ]))

def calc_mdd_and_return(prices):
    cum_ret = (prices.iloc[-1] / prices.iloc[0]) - 1
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    mdd = drawdown.min()
    return cum_ret, mdd

def main():
    tickers = get_etf_list()
    # Adding a few more prominent ones
    tickers += ["SPLG", "SOXL", "QQQM", "IGV", "FDN", "VUG", "IWF"]
    tickers = list(set(tickers))
    if 'SPY' not in tickers:
        tickers.append('SPY')

    print(f"Downloading data for {len(tickers)} ETFs (10 years)...")
    
    # 10 Years range roughly: 2016-04-13 to 2026-04-13
    start_date = "2016-04-12"
    end_date = "2026-04-12"
    
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        if 'Adj Close' in data.columns.levels[0]:
            price_df = data['Adj Close']
        elif 'Close' in data.columns.levels[0]:
            price_df = data['Close']
        else:
            price_df = data.xs('Close', level=0, axis=1, drop_level=False)
            price_df.columns = price_df.columns.droplevel(0)
    else:
        price_df = data
    
    print(f"Initial shape of price data: {price_df.shape}")
    
    # Check 10-year history: Must have valid data in the first 10 rows
    valid_tickers = []
    for ticker in price_df.columns:
        if not price_df[ticker].iloc[:10].isna().all():
            valid_tickers.append(ticker)
            
    print(f"ETFs with >=10 years history: {len(valid_tickers)}")
    
    if 'SPY' not in valid_tickers:
        print("Error: SPY not in valid tickers.")
        return
        
    prices = price_df[valid_tickers].dropna(axis=0, how='all')
    prices = prices.ffill().bfill()
    
    spy_ret, spy_mdd = calc_mdd_and_return(prices["SPY"])
    print(f"\nSPY Baseline: Return = {spy_ret*100:.2f}%, Max Drawdown = {spy_mdd*100:.2f}%")
    
    results = []
    for ticker in valid_tickers:
        if ticker == "SPY":
            continue
        ret, mdd = calc_mdd_and_return(prices[ticker])
        if ret > spy_ret:
            results.append({
                "ETF": ticker,
                "Return (%)": round(ret * 100, 2),
                "Max Drawdown (%)": round(mdd * 100, 2),
                "Return/Drawdown": round(ret / abs(mdd), 2)
            })
            
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by="Return (%)", ascending=False)
        print("\nETFs beating SPY Summary:")
        print(df_results.head(20).to_string(index=False))
        
        # Save table in markdown format and csv format
        md_table = df_results.to_markdown(index=False)
        with open("outperforming_etfs.md", "w") as f:
            f.write("# ETFs Beating S&P 500 (10-Year Period)\n\n")
            f.write(md_table)
            
        df_results.to_csv("outperforming_etfs.csv", index=False)
        
        # Create Plotly Chart for top 15 beating SPY
        top_15 = df_results.head(15)["ETF"].tolist()
        fig = go.Figure()
        
        # Add SPY
        norm_spy = prices["SPY"] / prices["SPY"].iloc[0] * 100
        fig.add_trace(go.Scatter(x=prices.index, y=norm_spy, mode='lines', name='SPY', line=dict(color='white', width=4)))
        
        for ticker in top_15:
            norm_price = prices[ticker] / prices[ticker].iloc[0] * 100
            fig.add_trace(go.Scatter(x=prices.index, y=norm_price, mode='lines', name=ticker, line=dict(width=1.5)))
            
        fig.update_layout(
            title="Top 15 Outperforming ETFs vs S&P 500 (10-Year Cumulative Return)",
            xaxis_title="Date",
            yaxis_title="Normalized Return (Base = 100)",
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        fig.write_html("etf_comparison.html")
        print("\nGenerated etf_comparison.html and outperforming_etfs.csv")
    else:
        print("\nNo ETFs beat SPY.")

if __name__ == '__main__':
    main()
