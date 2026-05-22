import yfinance as yf
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def verify():
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=10)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print("--- DATA ACCURACY VERIFICATION ---")
    print(f"Date Range: {start_str} to {end_str}")
    
    # 1. Check Benchmark Match
    spy = yf.download('SPY', start=start_str, end=end_str, progress=False)['Close']
    spy = spy.squeeze().ffill().dropna()
    start_price = spy.iloc[0]
    end_price = spy.iloc[-1]
    
    math_return = (end_price / start_price - 1) * 100
    
    spy_rets = spy.pct_change().dropna()
    cum_rets = (1 + spy_rets).cumprod()
    series_return = (cum_rets.iloc[-1] - 1) * 100
    
    print("\n[Benchmark - SPY]")
    print(f"Start Price (First valid day): ${start_price:.2f}")
    print(f"End Price (Last valid day): ${end_price:.2f}")
    print(f"Raw Math Return (End/Start - 1): {math_return:.2f}%")
    print(f"Cumprod Series Return: {series_return:.2f}%")
    if abs(math_return - series_return) < 0.1:
        print("-> Benchmark calculations MATCH optimally.")
    else:
        print("-> WARNING: Benchmark calculation discrepancy.")
        
    # 2. Check a Sector Portfolio calculation
    tech_tickers = ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL']
    print("\n[Sector Portfolio - Tech (AAPL, MSFT, NVDA, AVGO, ORCL)]")
    
    df = yf.download(tech_tickers, start=start_str, end=end_str, progress=False)['Close']
    df = df.ffill().dropna(how='all')
    
    # Buy and hold raw return (Assume $100 in each = $500 total start)
    start_prices = df.iloc[0]
    end_prices = df.iloc[-1]
    shares_bought = 100 / start_prices
    end_value = (shares_bought * end_prices).sum()
    b_and_h_return = (end_value / 500 - 1) * 100
    
    # Daily Rebalanced equal-weight return
    daily_rets = df.pct_change().dropna()
    port_daily_rets = daily_rets.mean(axis=1) # 20% weight every day
    dr_cum_rets = (1 + port_daily_rets).cumprod()
    dr_return = (dr_cum_rets.iloc[-1] - 1) * 100
    
    print(f"Buy-and-Hold Equal Weight Return: {b_and_h_return:.2f}%")
    print(f"Daily Rebalanced Equal Weight Return: {dr_return:.2f}%")
    print(f"\nThe dashboard script uses standard Daily Rebalanced equal weighting, meaning it assumes winners are trimmed and losers are bought daily to maintain exact 20% sector allocation. This perfectly tracks the dynamic behavior of an equal-weight index.")

if __name__ == "__main__":
    verify()
