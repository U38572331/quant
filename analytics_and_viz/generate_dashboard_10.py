import json

with open("capital_data_10.json", "r") as f:
    data = json.load(f)

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Premium Portfolio Analytics (10 Tickers)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        :root {
            --bg-color: #0b0e14;
            --container-bg: rgba(23, 27, 34, 0.7);
            --text-main: #e6edf3;
            --text-dim: #848d97;
            --accent-blue: #2f81f7;
            --accent-orange: #f78166;
            --border-color: rgba(255, 255, 255, 0.1);
        }
        body { 
            font-family: 'Inter', sans-serif; 
            margin: 0; 
            padding: 0; 
            background-color: var(--bg-color); 
            color: var(--text-main);
            overflow-x: hidden;
        }
        .dashboard-wrapper {
            max-width: 1400px;
            margin: 40px auto;
            padding: 0 20px;
        }
        header {
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        h1 { margin: 0; font-weight: 600; font-size: 2.5rem; letter-spacing: -0.025em; }
        .subtitle { color: var(--text-dim); margin-top: 5px; font-size: 1.1rem; }
        .stats { display: flex; gap: 40px; }
        .stat-item { display: flex; flex-direction: column; }
        .stat-label { font-size: 0.8rem; text-transform: uppercase; color: var(--text-dim); letter-spacing: 0.1em; }
        .stat-value { font-size: 1.5rem; font-weight: 600; color: var(--accent-blue); }

        .chart-container {
            background: var(--container-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            position: relative;
        }
        #chart { width: 100%; height: 600px; }
        .tip { 
            position: absolute; 
            top: 24px; 
            right: 24px; 
            font-size: 0.8rem; 
            color: var(--text-dim);
            background: rgba(255,255,255,0.05);
            padding: 4px 12px;
            border-radius: 20px;
        }
    </style>
</head>
<body>
    <div class="dashboard-wrapper">
        <header>
            <div>
                <h1>15-Year Portfolio Analytics</h1>
                <p class="subtitle">Multi-year Capital Path • Total Return Performance • 10 Financial Tickers vs SPX TR</p>
                <p class="subtitle" style="font-size: 0.9rem; margin-top: 10px; color: #a1b0c0;">
                    Holdings (10% each): BX, KKR, APO, ARES, MSCI, SPGI, BLK, CME, CBOE, NDAQ
                </p>
            </div>
        </header>

        <section>
            <h2 style="margin-bottom: 20px; font-weight: 500;">Scenario 1: Lump Sum Performance ($1,000,000 Initial)</h2>
            <div class="chart-container">
                <span class="tip">Scroll to zoom • Drag to pan</span>
                <div id="chart_lump"></div>
            </div>
        </section>

        <section style="margin-top: 60px;">
            <h2 style="margin-bottom: 20px; font-weight: 500;">Scenario 2: Lump Sum Performance ($10,000 Initial)</h2>
            <div class="chart-container">
                <span class="tip">Scroll to zoom • Drag to pan</span>
                <div id="chart_lump_small"></div>
            </div>
        </section>

        <section style="margin-top: 60px;">
            <h2 style="margin-bottom: 20px; font-weight: 500;">Scenario 3: Monthly DCA Performance ($1M initial + $1k/mo)</h2>
            <div class="chart-container">
                <span class="tip">Scroll to zoom • Drag to pan</span>
                <div id="chart_dca"></div>
            </div>
        </section>

        <section style="margin-top: 60px;">
            <h2 style="margin-bottom: 20px; font-weight: 500;">Independent Annual Analysis: Jan 1 to Dec 31</h2>
            <p class="subtitle">Side-by-side comparison of annual total returns for each independent calendar year.</p>
            <div class="chart-container">
                <div id="chart_annual"></div>
            </div>
        </section>
    </div>

    <script>
        const data = {data_placeholder};
        
        function createTrace(x, y, name, color, isDashed=false) {
            return {
                x: x,
                y: y,
                type: 'scatter',
                mode: 'lines',
                name: name,
                line: { color: color, width: 3, shape: 'spline', dash: isDashed ? 'dot' : 'solid' },
                fill: isDashed ? 'none' : 'tozeroy',
                fillcolor: isDashed ? 'none' : 'rgba(68, 147, 248, 0.05)'
            };
        }

        const commonLayout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#e6edf3', family: 'Inter' },
            margin: { t: 40, b: 40, l: 60, r: 20 },
            hovermode: 'x unified',
            dragmode: 'pan',
            hoverlabel: { bgcolor: '#161b22', bordercolor: '#30363d', font: { color: '#e6edf3' } },
            legend: { orientation: 'h', y: 1.1, x: 0, font: { size: 12 } },
            xaxis: { 
                gridcolor: 'rgba(255,255,255,0.05)', 
                linecolor: 'rgba(255,255,255,0.1)',
                title: { text: 'Timeline', font: { size: 10, color: '#848d97' } }
            },
            yaxis: { 
                gridcolor: 'rgba(255,255,255,0.05)', 
                linecolor: 'rgba(255,255,255,0.1)',
                tickformat: '$,.0f',
                title: { text: 'Capital Value ($)', font: { size: 10, color: '#848d97' } }
            }
        };

        const config = {
            responsive: true,
            scrollZoom: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        };

        // Chart 1: Lump Sum
        const traceLumpP = createTrace(data.dates, data.lump_sum.portfolio, '10-Ticker Portfolio (Lump Sum)', '#4493f8');
        const traceLumpS = createTrace(data.dates, data.lump_sum.spx, 'S&P 500 TR (Lump Sum)', '#f78166', true);
        Plotly.newPlot('chart_lump', [traceLumpP, traceLumpS], commonLayout, config);

        // Chart 2: Lump Sum Small (10k)
        const traceLumpSmallP = createTrace(data.dates, data.lump_sum_small.portfolio, '10-Ticker Portfolio ($10k)', '#4493f8');
        const traceLumpSmallS = createTrace(data.dates, data.lump_sum_small.spx, 'S&P 500 TR ($10k)', '#f78166', true);
        Plotly.newPlot('chart_lump_small', [traceLumpSmallP, traceLumpSmallS], commonLayout, config);

        // Chart 3: DCA
        const traceDcaP = createTrace(data.dates, data.dca.portfolio, '10-Ticker Portfolio (DCA)', '#4493f8');
        const traceDcaS = createTrace(data.dates, data.dca.spx, 'S&P 500 TR (DCA)', '#f78166', true);
        Plotly.newPlot('chart_dca', [traceDcaP, traceDcaS], commonLayout, config);

        // Chart 4: Annual Bar Chart
        const annualYears = data.annual.map(d => d.year);
        const annualP = data.annual.map(d => d.portfolio);
        const annualS = data.annual.map(d => d.spx);

        const traceAnnualP = {
            x: annualYears,
            y: annualP,
            name: 'Portfolio Return %',
            type: 'bar',
            marker: { color: '#4493f8' },
            text: annualP.map(v => v + '%'),
            textposition: 'outside'
        };

        const traceAnnualS = {
            x: annualYears,
            y: annualS,
            name: 'S&P 500 TR Return %',
            type: 'bar',
            marker: { color: '#f78166' },
            text: annualS.map(v => v + '%'),
            textposition: 'outside'
        };

        const annualLayout = {
            ...commonLayout,
            barmode: 'group',
            dragmode: false,
            yaxis: { 
                ...commonLayout.yaxis, 
                ticksuffix: '%', 
                tickformat: '.1f',
                title: { text: 'Annual Return (%)', font: { size: 10, color: '#848d97' } }
            }
        };

        Plotly.newPlot('chart_annual', [traceAnnualP, traceAnnualS], annualLayout, config);
    </script>
</body>
</html>
"""

full_html = html_template.replace("{data_placeholder}", json.dumps(data))

with open("dashboard_10_ticker.html", "w", encoding="utf-8") as f:
    f.write(full_html)

print("Self-contained dashboard_10_ticker.html generated.")
