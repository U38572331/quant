import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

SURVIVORS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "BRK-B", "UNH", "JNJ", "XOM", "JPM", "V", "PG", "MA", "NVDA",
    "HD", "CVX", "KO", "PEP", "ABBV", "COST", "AVGO", "MCD", "CSCO", "TMUS", "CRM", "LIN", "ACN", "ADBE", "NFLX",
    "AMD", "TXN", "DIS", "ORCL", "HON", "PM", "AMAT", "INTU", "CAT", "UNP", "LOW", "IBM", "QCOM", "AMGN", "GE",
    "RTX", "ISRG", "GS", "SPGI", "BKNG", "NOW", "TMO", "MS", "INTC", "SYK", "ELV", "PLD", "AXP", "BLK", "DE",
    "MDT", "MMC", "TJX", "BSX", "PGR", "ADP", "CB", "ETN", "MU", "SCHW", "VRTX", "COP", "LMT", "CI", "GILD",
    "ADI", "ABT", "EQIX", "REGN", "ITW", "CVS", "PANW", "ICE", "MCO", "WM", "CME", "SNPS", "FDX", "CDNS", "TGT"
]

BENCHMARK = "SPY"
START_DATE = "2016-04-25"
END_DATE = "2026-04-20"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\sp500_survivors"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "survivors_dashboard.html")

def safe_tolist(obj):
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    if hasattr(obj, 'values'):
        if hasattr(obj.values, 'tolist'):
            return obj.values.tolist()
    return list(obj)

def analyze():
    print(f"Downloading benchmark {BENCHMARK}...")
    bench_data = yf.download(BENCHMARK, start=START_DATE, end=END_DATE, progress=False)
    if bench_data.empty: return None
    
    if isinstance(bench_data.columns, pd.MultiIndex):
        spy_prices = bench_data.xs('Adj Close', axis=1, level=0) if 'Adj Close' in bench_data.columns.levels[0] else bench_data.xs('Close', axis=1, level=0)
    else:
        spy_prices = bench_data['Adj Close'] if 'Adj Close' in bench_data.columns else bench_data['Close']
    
    spy_prices = spy_prices.ffill().dropna()
    if isinstance(spy_prices, pd.DataFrame):
        spy_prices = spy_prices.iloc[:, 0]
    
    print(f"Downloading {len(SURVIVORS)} survivors...")
    all_prices = {}
    valid_tickers = []
    
    chunk_size = 30
    for i in range(0, len(SURVIVORS), chunk_size):
        chunk = SURVIVORS[i:i+chunk_size]
        chunk = [t.replace('.', '-') for t in chunk]
        data = yf.download(chunk, start=START_DATE, end=END_DATE, progress=False)
        
        if not data.empty:
            p = None
            if isinstance(data.columns, pd.MultiIndex):
                for attr in ['Adj Close', 'Close']:
                    if attr in data.columns.levels[0]:
                        p = data[attr]
                        break
            else:
                p = data[['Adj Close']] if 'Adj Close' in data.columns else data[['Close']]
                
            if p is not None:
                for col in p.columns:
                    series = p[col].ffill()
                    if not series.dropna().empty and len(series.dropna()) > (len(spy_prices) * 0.7):
                        all_prices[col] = series
                        valid_tickers.append(col)

    if not all_prices:
        print("Error: No survivor data captured.")
        return None
        
    prices_df = pd.DataFrame(all_prices).reindex(spy_prices.index).ffill()
    returns = prices_df.pct_change()
    survivor_port = (1 + returns.mean(axis=1).fillna(0)).cumprod() * 100
    
    spy_cum = (1 + spy_prices.pct_change().fillna(0)).cumprod() * 100
    
    perf = {
        "Dates": [d.strftime('%Y-%m-%d') for d in spy_cum.index],
        "Survivors": safe_tolist(survivor_port),
        "SPY": safe_tolist(spy_cum),
        "TickerCount": len(valid_tickers)
    }
    return perf

def generate_html(perf):
    if not perf: return
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>S&P 500 Survivors vs Index</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d10; color: #eee; margin: 0; padding: 20px; }
        .container { max-width: 1400px; margin: auto; }
        .header { border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .chart-box { background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; height: 70vh; }
        .stats { margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .stat-card { background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>S&P 500 Survivors vs Benchmark (10-Year Comparison)</h1>
        <p>Comparing <b>{{count}} persistent companies</b> (in the index since 2016) vs the Benchmark (SPY).</p>
        <p style="color:#8b949e; font-size:0.8rem;">Equal-weighted Survivor Portfolio vs Cap-weighted SPY.</p>
    </div>
    <div class="chart-box" id="chart"></div>
    <div class="stats">
        <div class="stat-card">
            <h3>Survivors Portfolio</h3>
            <div id="surv-perf" style="font-size: 2.5rem; color: #bc8cff; font-weight: bold;"></div>
        </div>
        <div class="stat-card">
            <h3>S&P 500 (SPY)</h3>
            <div id="spy-perf" style="font-size: 2.5rem; color: #ffffff; font-weight: bold;"></div>
        </div>
    </div>
</div>
<script>
    const data = JSON_DATA;
    const chartData = [
        { x: data.Dates, y: data.Survivors, name: '10-Year Survivors (EQW)', line: {color: '#bc8cff', width: 3} },
        { x: data.Dates, y: data.SPY, name: 'S&P 500 (SPY)', line: {color: '#ffffff', width: 2, dash: 'dot'} }
    ];
    Plotly.newPlot('chart', chartData, {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#8b949e' },
        margin: { t: 20 },
        xaxis: { gridcolor: '#21262d' },
        yaxis: { 
            gridcolor: '#21262d', title: 'Growth of $100',
            type: 'log'
        },
        hovermode: 'x unified'
    }, {responsive: true});
    
    const sRet = ((data.Survivors[data.Survivors.length-1] / 100) - 1) * 100;
    const bRet = ((data.SPY[data.SPY.length-1] / 100) - 1) * 100;
    document.getElementById('surv-perf').innerText = sRet.toFixed(1) + '%';
    document.getElementById('spy-perf').innerText = bRet.toFixed(1) + '%';
</script>
</body>
</html>
    """.replace("JSON_DATA", json.dumps(perf)).replace("{{count}}", str(perf['TickerCount']))
    
    with open(OUTPUT_FILE, "w") as f: f.write(html)
    print(f"Generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    p = analyze()
    generate_html(p)
