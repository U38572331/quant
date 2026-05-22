import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Define sectors and their top 5 stocks
SECTORS = {
    'Information Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL'],
    'Health Care': ['LLY', 'UNH', 'JNJ', 'MRK', 'ABBV'],
    'Financials': ['JPM', 'V', 'MA', 'BAC', 'WFC'],
    'Consumer Discretionary': ['AMZN', 'TSLA', 'HD', 'MCD', 'TMUS'],
    'Communication Services': ['META', 'GOOGL', 'NFLX', 'DIS', 'CMCSA'],
    'Industrials': ['CAT', 'GE', 'RTX', 'LMT', 'HON'],
    'Consumer Staples': ['WMT', 'PG', 'COST', 'KO', 'PEP'],
    'Energy': ['XOM', 'CVX', 'COP', 'MPC', 'EOG'],
    'Utilities': ['NEE', 'SO', 'DUK', 'CEG', 'AEP'],
    'Real Estate': ['PLD', 'AMT', 'EQIX', 'WELL', 'SPG'],
    'Materials': ['LIN', 'SHW', 'FCX', 'ECL', 'NEM']
}
BENCHMARK = 'SPY'

def calculate_max_drawdown(cum_returns):
    rolling_max = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - rolling_max) / rolling_max
    return np.min(drawdowns) * 100 # In percentage

def fetch_and_calculate():
    print("Initializing Data Fetch...")
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=10)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Fetching S&P 500 benchmark data ({BENCHMARK}) from {start_str} to {end_str}")
    benchmark_data = yf.download(BENCHMARK, start=start_str, end=end_str, progress=False)['Close']
    
    if isinstance(benchmark_data, pd.DataFrame):
        benchmark_data = benchmark_data.squeeze()
        
    benchmark_data = benchmark_data.ffill()
    benchmark_returns = benchmark_data.pct_change().dropna()
    benchmark_cum = (1 + benchmark_returns).cumprod()
    
    # Calculate Benchmark Metrics
    bm_years = len(benchmark_cum) / 252.0
    bm_total_return = (benchmark_cum.iloc[-1] - 1) * 100
    bm_cagr = ((benchmark_cum.iloc[-1] ** (1 / bm_years)) - 1) * 100
    bm_md = calculate_max_drawdown(benchmark_cum)
    
    chart_data = {
        'labels': benchmark_cum.index.strftime('%Y-%m-%d').tolist(),
        'datasets': [
            {
                'label': 'S&P 500 (Benchmark)',
                'data': (benchmark_cum * 100).round(2).tolist(),
            }
        ]
    }
    
    metrics = {
        'S&P 500 (Benchmark)': {
            'totalReturn': round(bm_total_return, 2),
            'cagr': round(bm_cagr, 2),
            'maxDrawdown': round(bm_md, 2)
        }
    }
    
    # Track the common date index
    common_index = benchmark_cum.index
    
    for sector_name, tickers in SECTORS.items():
        print(f"Fetching data for {sector_name}: {', '.join(tickers)}")
        try:
            sector_df = yf.download(tickers, start=start_str, end=end_str, progress=False)['Close']
            sector_df = sector_df.ffill()
            
            # Reindex to common index to align daily returns properly
            sector_df = sector_df.reindex(common_index).ffill()
            
            # Daily returns
            daily_rets = sector_df.pct_change().dropna()
            
            # Equal weight (average of daily returns)
            port_daily_rets = daily_rets.mean(axis=1)
            
            # Add implicit zero return for the first date
            port_daily_rets = pd.concat([pd.Series([0.0], index=[common_index[0]]), port_daily_rets])
            
            port_cum = (1 + port_daily_rets).cumprod()
            port_cum = port_cum.reindex(common_index).ffill()
            
            # Align with chart labels (trimming any missing dates if need be, but should match common index)
            dataset_values = (port_cum * 100).round(2).tolist()
            
            chart_data['datasets'].append({
                'label': sector_name,
                'data': dataset_values
            })
            
            years = len(port_cum) / 252.0
            tot_ret = (port_cum.iloc[-1] - 1) * 100
            cagr = ((port_cum.iloc[-1] ** (1 / years)) - 1) * 100
            md = calculate_max_drawdown(port_cum)
            
            metrics[sector_name] = {
                'totalReturn': round(tot_ret, 2),
                'cagr': round(cagr, 2),
                'maxDrawdown': round(md, 2)
            }
            
        except Exception as e:
            print(f"Error fetching data for {sector_name}: {str(e)}")

    return chart_data, metrics

def generate_html(chart_data, metrics):
    print("Generating HTML Dashboard...")
    # Escape data for javascript injection
    chart_json = json.dumps(chart_data)
    metrics_json = json.dumps(metrics)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>10-Year Sector Portfolio Analysis</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-color: #0f172a;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --accent: #38bdf8;
            --positive: #10b981;
            --negative: #ef4444;
        }}
        body {{
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 15% 50%, rgba(56, 189, 248, 0.05), transparent 25%),
                radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.05), transparent 25%);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p.subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
            max-width: 600px;
            margin: 0 auto;
        }}
        .glass-panel {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            margin-bottom: 40px;
        }}
        .chart-container {{
            position: relative;
            height: 60vh;
            width: 100%;
        }}
        
        /* Table Styles */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .metric-card {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(56, 189, 248, 0.1);
            border-color: rgba(56, 189, 248, 0.3);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .sector-name {{
            font-weight: 600;
            font-size: 1.1rem;
            color: #e2e8f0;
        }}
        .sector-color-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .metric-label {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        .metric-value {{
            font-weight: 600;
        }}
        .positive {{ color: var(--positive); }}
        .negative {{ color: var(--negative); }}

        /* Top 5 list inside metric card */
        .top-stocks {{
            margin-top: 15px;
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
            border-top: 1px dashed rgba(255, 255, 255, 0.1);
            padding-top: 10px;
        }}
        .tech-list {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 5px;
        }}
        .badge {{
            background: rgba(255,255,255,0.05);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.1);
        }}

        @media (max-width: 768px) {{
            .chart-container {{ height: 50vh; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <h1>10-Year Sector Performance Dashboard</h1>
        <p class="subtitle">An equal-weight (20% each) comparison of the top 5 stocks in all 11 GICS sectors against the S&P 500, visualizing cumulative growth over the past decade.</p>
    </header>

    <div class="glass-panel">
        <h2 style="margin-top: 0; font-size: 1.2rem; color: #cbd5e1; margin-bottom: 20px;">Cumulative Growth (Base = 100%)</h2>
        <div class="chart-container">
            <canvas id="performanceChart"></canvas>
        </div>
    </div>

    <div class="metrics-grid" id="metricsGrid">
        <!-- Cards injected dynamically -->
    </div>
</div>

<script>
    const chartData = {chart_json};
    const metricsData = {metrics_json};
    const sectorsDict = {json.dumps(SECTORS)};

    const colors = [
        '#ffffff', // S&P 500
        '#38bdf8', '#818cf8', '#f472b6', '#fbbf24', '#34d399',
        '#a78bfa', '#fb923c', '#f87171', '#4ade80', '#2dd4bf', '#a3e635'
    ];

    // Format chart dataset colors
    chartData.datasets.forEach((ds, idx) => {{
        const isBenchmark = ds.label.includes('Benchmark');
        ds.borderColor = colors[idx % colors.length];
        ds.borderWidth = isBenchmark ? 3 : 2;
        ds.pointRadius = 0;
        ds.pointHoverRadius = 4;
        ds.tension = 0.2;
        if (isBenchmark) {{
            ds.borderDash = [5, 5];
        }}
    }});

    // Render Chart
    const ctx = document.getElementById('performanceChart').getContext('2d');
    new Chart(ctx, {{
        type: 'line',
        data: chartData,
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                mode: 'index',
                intersect: false,
            }},
            plugins: {{
                legend: {{
                    labels: {{
                        color: '#94a3b8',
                        usePointStyle: true,
                        boxWidth: 8,
                        font: {{ family: 'Inter', size: 12 }}
                    }}
                }},
                tooltip: {{
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    boxPadding: 6,
                    callbacks: {{
                        label: function(context) {{
                            let label = context.dataset.label || '';
                            if (label) {{ label += ': '; }}
                            if (context.parsed.y !== null) {{
                                label += context.parsed.y.toFixed(2) + '%';
                            }}
                            return label;
                        }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }},
                    ticks: {{ color: '#64748b', maxTicksLimit: 12 }}
                }},
                y: {{
                    grid: {{ color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }},
                    ticks: {{
                        color: '#64748b',
                        callback: function(value) {{ return value + '%'; }}
                    }}
                }}
            }}
        }}
    }});

    // Format Number Helpet
    const formatPct = (val) => {{
        const formatted = val.toFixed(2) + '%';
        return val >= 0 ? '+' + formatted : formatted;
    }};

    // Render Metrics Cards
    const grid = document.getElementById('metricsGrid');
    
    // Sort items by Total Return
    const sortedKeys = Object.keys(metricsData).sort((a, b) => metricsData[b].totalReturn - metricsData[a].totalReturn);

    sortedKeys.forEach(sector => {{
        const m = metricsData[sector];
        const dsIndex = chartData.datasets.findIndex(d => d.label === sector);
        const dotColor = dsIndex >= 0 ? chartData.datasets[dsIndex].borderColor : '#ffffff';
        
        let stocksHtml = '';
        if (sectorsDict[sector]) {{
            const badges = sectorsDict[sector].map(t => `<span class="badge">${{t}}</span>`).join('');
            stocksHtml = `
                <div class="top-stocks">
                    Top Components
                    <div class="tech-list">${{badges}}</div>
                </div>
            `;
        }}

        const totClass = m.totalReturn >= 0 ? 'positive' : 'negative';
        const cagrClass = m.cagr >= 0 ? 'positive' : 'negative';

        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `
            <div class="card-header">
                <div class="sector-name">${{sector}}</div>
                <div class="sector-color-dot" style="background: ${{dotColor}}"></div>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total Return</span>
                <span class="metric-value ${{totClass}}">${{formatPct(m.totalReturn)}}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Ann. Return (CAGR)</span>
                <span class="metric-value ${{cagrClass}}">${{formatPct(m.cagr)}}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Max Drawdown</span>
                <span class="metric-value negative">${{m.maxDrawdown.toFixed(2)}}%</span>
            </div>
            ${{stocksHtml}}
        `;
        grid.appendChild(card);
    }});

</script>
</body>
</html>
    """
    
    out_path = os.path.join(os.path.dirname(__file__), 'sector_dashboard.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Success! Dashboard created at: {out_path}")

if __name__ == "__main__":
    c_data, m_data = fetch_and_calculate()
    generate_html(c_data, m_data)
