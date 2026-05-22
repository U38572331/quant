import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

# Configuration
GROUPS = {
    "Rule Makers": ["MSCI", "SPGI", "MCO", "CME", "ICE"],
    "Network Effects": ["V", "MA", "META", "GOOGL", "TCEHY"],
    "AI & Infrastructure": ["MSFT", "AMZN", "NVDA", "TSM", "ASML", "AVGO"],
    "Information Control": ["RELX", "TRI", "IQV"],
    "Physical Infrastructure": ["UNP", "CSX", "NEE", "WM", "XOM"]
}
BENCHMARK = "SPY"
START_DATE = "2014-01-01"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\monopoly_fortress"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "monopoly_dashboard.html")

def fetch_data():
    all_tickers = [t for g in GROUPS.values() for t in g] + [BENCHMARK]
    print(f"Fetching data for {len(all_tickers)} tickers...")
    data = yf.download(all_tickers, start=START_DATE, progress=False)
    
    # Handle column levels
    if isinstance(data.columns, pd.MultiIndex):
        if 'Adj Close' in data.columns.levels[0]:
            prices = data['Adj Close']
        else:
            prices = data['Close']
    else:
        prices = data
        
    return prices

def process_performance(prices):
    # Drop rows where everything is NaN (weekends/holidays)
    prices = prices.dropna(how='all')
    
    # Forward fill missing values (some ADRs might have slight gaps)
    prices = prices.ffill()
    
    # Calculate daily returns
    returns = prices.pct_change()
    
    # Cumulative returns (starting from 100)
    # We find the first date where all data is available or just start from 2014-01-01
    # Normalized to the first date having data for most tickers
    norm_prices = (1 + returns.fillna(0)).cumprod() * 100
    
    # Group Portfolios
    perf_data = {
        "Benchmark": norm_prices[BENCHMARK].tolist(),
        "Dates": [d.strftime('%Y-%m-%d') for d in norm_prices.index],
        "Groups": {}
    }
    
    group_stats = []

    for group_name, tickers in GROUPS.items():
        # Equal weighted portfolio return
        group_returns = returns[tickers].mean(axis=1)
        group_cum = (1 + group_returns.fillna(0)).cumprod() * 100
        
        perf_data["Groups"][group_name] = {
            "cumulative": group_cum.tolist(),
            "tickers": {t: norm_prices[t].tolist() for t in tickers}
        }
        
        # Stats
        total_ret = (group_cum.iloc[-1] / group_cum.iloc[0]) - 1
        years = (norm_prices.index[-1] - norm_prices.index[0]).days / 365.25
        cagr = (1 + total_ret) ** (1 / years) - 1
        
        # Max Drawdown
        rolling_max = group_cum.cummax()
        drawdown = (group_cum - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        group_stats.append({
            "name": group_name,
            "cagr": f"{cagr:.1%}",
            "mdd": f"{max_dd:.1%}",
            "total": f"{total_ret:.0%}"
        })

    # Benchmark stats
    bench_cum = norm_prices[BENCHMARK]
    bench_total = (bench_cum.iloc[-1] / bench_cum.iloc[0]) - 1
    bench_years = (norm_prices.index[-1] - norm_prices.index[0]).days / 365.25
    bench_cagr = (1 + bench_total) ** (1 / bench_years) - 1
    bench_rolling_max = bench_cum.cummax()
    bench_drawdown = (bench_cum - bench_rolling_max) / bench_rolling_max
    bench_mdd = bench_drawdown.min()
    
    group_stats.insert(0, {
        "name": "S&P 500 (SPY)",
        "cagr": f"{bench_cagr:.1%}",
        "mdd": f"{bench_mdd:.1%}",
        "total": f"{bench_total:.0%}"
    })

    return perf_data, group_stats

def generate_html(perf_data, group_stats):
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monopoly Stocks Performance Hub</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {
            background-color: #0b0d10;
            color: #f0f0f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        header {
            padding: 20px 40px;
            border-bottom: 1px solid #2d333b;
            background: #161b22;
        }

        h1 { margin: 0; font-size: 1.5rem; color: #fff; }
        .subtitle { color: #8b949e; font-size: 0.9rem; margin-top: 5px; }

        .container {
            flex: 1;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }

        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            padding: 15px;
            border-radius: 6px;
        }

        .stat-name { color: #8b949e; font-size: 0.8rem; margin-bottom: 5px; font-weight: 600; }
        .stat-total { font-size: 1.25rem; font-weight: bold; margin-bottom: 5px; }
        .stat-meta { font-size: 0.75rem; color: #58a6ff; }

        .chart-wrapper {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 20px;
            flex: 1;
            min-height: 70vh;
        }

        #main-chart { height: 100%; width: 100%; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: #161b22;
            border-radius: 6px;
            overflow: hidden;
        }

        th, td {
            text-align: left;
            padding: 12px 15px;
            border-bottom: 1px solid #30363d;
        }

        th { background: #21262d; color: #8b949e; font-size: 0.85rem; }
        tr:hover { background: #2d333b; }

        .trend-up { color: #3fb950; }
        .trend-down { color: #f85149; }

        footer {
            padding: 20px 40px;
            color: #484f58;
            font-size: 0.75rem;
            text-align: center;
        }
    </style>
</head>
<body>

<header>
    <h1>Monopoly Stocks Analysis Hub</h1>
    <div class="subtitle">Normalized Performance Comparison (2014 - Present) | $100 Adjusted Close Baseline</div>
</header>

<div class="container">
    <div class="stats-grid" id="stats-cards"></div>

    <div class="chart-wrapper">
        <div id="main-chart"></div>
    </div>

    <div class="stat-card" style="padding: 0;">
        <table id="summary-table">
            <thead>
                <tr>
                    <th>Group Name</th>
                    <th>Total Return</th>
                    <th>CAGR (Ann.)</th>
                    <th>Max Drawdown</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
</div>

<footer>
    All data sourced via Yahoo Finance (Adj Close). Portfolios are equal-weighted and rebalanced daily.
</footer>

<script>
    const data = JSON_DATA_HERE;
    const stats = STATS_DATA_HERE;

    function renderUI() {
        // Render Cards
        const cardArea = document.getElementById('stats-cards');
        cardArea.innerHTML = stats.map(s => `
            <div class="stat-card" style="border-left: 4px solid ${getColor(s.name)}">
                <div class="stat-name">${s.name}</div>
                <div class="stat-total">${s.total}</div>
                <div class="stat-meta">MDD: ${s.mdd}</div>
            </div>
        `).join('');

        // Render Table
        const tbody = document.querySelector('#summary-table tbody');
        tbody.innerHTML = stats.map(s => `
            <tr>
                <td style="color:${getColor(s.name)}; font-weight:bold;">${s.name}</td>
                <td>${s.total}</td>
                <td>${s.cagr}</td>
                <td class="trend-down">${s.mdd}</td>
            </tr>
        `).join('');
    }

    function getColor(name) {
        const colors = {
            "S&P 500 (SPY)": "#ffffff",
            "Rule Makers": "#ffcc00",
            "Network Effects": "#1f6feb",
            "AI & Infrastructure": "#bc8cff",
            "Information Control": "#3fb950",
            "Physical Infrastructure": "#f78166"
        };
        return colors[name] || "#ffffff";
    }

    function plot() {
        const traces = [];
        traces.push({
            x: data.Dates, y: data.Benchmark,
            name: 'S&P 500', line: { color: '#ffffff', width: 2, dash: 'dot' },
            type: 'scatter'
        });

        Object.keys(data.Groups).forEach(name => {
            traces.push({
                x: data.Dates, y: data.Groups[name].cumulative,
                name: name, line: { color: getColor(name), width: 2.5 },
                type: 'scatter'
            });
        });

        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#8b949e' },
            hovermode: 'x unified',
            xaxis: { gridcolor: '#21262d', linecolor: '#30363d', tickfont: { size: 10 } },
            yaxis: { 
                gridcolor: '#21262d', linecolor: '#30363d', 
                title: 'Growth of $100', 
                type: 'log' // Log scale makes it much easier to see early performance differences
            },
            margin: { t: 30, b: 60, l: 60, r: 20 },
            legend: { x: 0, y: 1.1, orientation: 'h' }
        };

        Plotly.newPlot('main-chart', traces, layout, { responsive: true, displaylogo: false });
    }

    renderUI();
    plot();
</script>
</body>
</html>
    """
    
    final_html = html_template.replace("JSON_DATA_HERE", json.dumps(perf_data))
    final_html = final_html.replace("STATS_DATA_HERE", json.dumps(group_stats))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"Dashboard generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    prices = fetch_data()
    perf_data, group_stats = process_performance(prices)
    generate_html(perf_data, group_stats)
