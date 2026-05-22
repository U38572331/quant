import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def calc_mdd(prices):
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    return drawdown.min()

def main():
    tickers = ["SOXL", "TQQQ", "SMH", "SOXX", "UPRO", "VGT", "XLK", "QQQ", "ARKW", "ARKQ", "COPX", "XME", "BHP", "SPY"]
    
    print(f"Downloading max historical data for {len(tickers)} ETFs...")
    data = yf.download(tickers, period="max", auto_adjust=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        if 'Adj Close' in data.columns.levels[0]:
            prices = data['Adj Close']
        elif 'Close' in data.columns.levels[0]:
            prices = data['Close']
        else:
            prices = data.xs('Close', level=0, axis=1, drop_level=False)
            prices.columns = prices.columns.droplevel(0)
    else:
        prices = data

    results = []
    
    # Calculate Max History relative to SPY
    for ticker in tickers:
        if ticker == "SPY":
            continue
            
        valid_prices = prices[ticker].dropna()
        if len(valid_prices) == 0:
            continue
            
        start_date = valid_prices.index[0]
        end_date = valid_prices.index[-1]
        
        # Calculate years between start and end using precise datetime difference
        years = (end_date - start_date).days / 365.25
        
        # Ticker metrics
        t_start_price = valid_prices.iloc[0]
        t_end_price = valid_prices.iloc[-1]
        t_ret = (t_end_price / t_start_price) - 1
        t_cagr = ((t_end_price / t_start_price) ** (1/years)) - 1 if years > 0 else 0
        t_mdd = calc_mdd(valid_prices)
        
        # SPY metrics matched to the same dates
        spy_valid = prices["SPY"].loc[start_date:end_date].dropna()
        if len(spy_valid) > 0:
            spy_start_price = spy_valid.iloc[0]
            spy_end_price = spy_valid.iloc[-1]
            spy_ret = (spy_end_price / spy_start_price) - 1
            spy_cagr = ((spy_end_price / spy_start_price) ** (1/years)) - 1 if years > 0 else 0
            spy_mdd = calc_mdd(spy_valid)
        else:
            # Fallback if SPY somehow missing
            spy_ret = 0
            spy_cagr = 0
            spy_mdd = 0
            
        results.append({
            "ETF": ticker,
            "Inception (Data Start)": start_date.strftime("%Y-%m-%d"),
            "Years": round(years, 1),
            "ETF Total Ret (%)": round(t_ret * 100, 2),
            "SPY Total Ret (%)": round(spy_ret * 100, 2),
            "ETF CAGR (%)": round(t_cagr * 100, 2),
            "SPY CAGR (%)": round(spy_cagr * 100, 2),
            "ETF Max Drawdown (%)": round(t_mdd * 100, 2),
            "SPY Max Drawdown (%)": round(spy_mdd * 100, 2)
        })

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="ETF CAGR (%)", ascending=False)
    
    md_table = df_results.to_markdown(index=False)
    with open("max_history_report.md", "w") as f:
        f.write("# Maximum History Performance Comparison vs SPY\n\n")
        f.write("此表格比較了特定 ETF 從其資料建立（Inception）至今，相較於同一時期標普 500 (SPY) 的總報酬率與年化報酬率(CAGR)。\n\n")
        f.write(md_table)
        
    df_results.to_csv("max_history_etfs.csv", index=False)
    
    # Normalized continuous plot
    fig = go.Figure()
    
    # Base SPY on its oldest valid date
    spy_full = prices["SPY"].dropna()
    spy_base_val = 100
    norm_spy = spy_full / spy_full.iloc[0] * spy_base_val
    fig.add_trace(go.Scatter(x=norm_spy.index, y=norm_spy, mode='lines', name='SPY', line=dict(color='white', width=4)))
    
    for ticker in tickers:
        if ticker == "SPY": continue
        v_prices = prices[ticker].dropna()
        if len(v_prices) == 0: continue
            
        sd = v_prices.index[0]
        # Match SPY's normalized value at ETF's start date
        if sd in norm_spy.index:
            spy_val_at_start = norm_spy.loc[sd]
        else:
            # Get nearest previous date
            spy_val_at_start = norm_spy.asof(sd)
            if pd.isna(spy_val_at_start):
                spy_val_at_start = spy_base_val # default if SPY starts later than ETF
                
        norm_t = v_prices / v_prices.iloc[0] * spy_val_at_start
        fig.add_trace(go.Scatter(x=norm_t.index, y=norm_t, mode='lines', name=ticker, line=dict(width=1.5)))

    # Use log scale on y-axis for better visibility of exponential growth
    fig.update_layout(
        title="Max History Normalized Equity Curves (Aligned to SPY Baseline) - Log Scale",
        xaxis_title="Date",
        yaxis_title="Normalized Value (Log Scale)",
        yaxis_type="log",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    fig.write_html("max_history_comparison.html")
    print("Execution completed successfully.")

if __name__ == "__main__":
    main()
