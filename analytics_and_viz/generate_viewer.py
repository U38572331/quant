import pandas as pd
import json
import os

def generate_viewer():
    trades_path = "backtest_trades.csv"
    if not os.path.exists(trades_path):
        print("Trades file not found.")
        return
        
    df = pd.read_csv(trades_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['CumPnL'] = df['PnL'].cumsum()
    
    # Prepare data for Lightweight Charts (time: 'YYYY-MM-DD', value: number)
    data_points = []
    for _, row in df.iterrows():
        data_points.append({
            "time": row['Date'].strftime('%Y-%m-%d'),
            "value": round(float(row['CumPnL']), 2)
        })
    
    # Remove duplicate times (Lightweight charts needs unique times or timestamps)
    # If multiple trades on same day, use the last one for that day
    unique_data = {}
    for pt in data_points:
        unique_data[pt["time"]] = pt["value"]
    
    final_data = [{"time": t, "value": v} for t, v in sorted(unique_data.items())]

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NQ Equity Viewer</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background-color: #0a0a0a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
    <div id="header">
        <div class="title">NQ STRATEGY EQUITY VIEWER</div>
        <div class="stats">2021-2025 | {len(df)} Trades | Double-click to Reset Zoom</div>
    </div>
    <div id="chart-container"></div>
    <div id="debug" style="position:fixed; bottom:10px; right:10px; color:#555; font-size:10px; pointer-events:none;"></div>
    
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const debug = document.getElementById('debug');
            const container = document.getElementById('chart-container');
            
            try {{
                const chart = LightweightCharts.createChart(container, {{
                    width: container.clientWidth || 800,
                    height: container.clientHeight || 540,
                    layout: {{
                        background: {{ type: 'solid', color: '#050505' }},
                        textColor: '#00ff88',
                        fontSize: 12,
                    }},
                    grid: {{
                        vertLines: {{ color: '#1a1a1a' }},
                        horzLines: {{ color: '#1a1a1a' }},
                    }},
                    timeScale: {{
                        borderColor: '#222',
                        timeVisible: true,
                        barSpacing: 5,
                    }},
                    rightPriceScale: {{
                        borderColor: '#222',
                        autoScale: true,
                    }},
                }});

                const series = chart.addLineSeries({{
                    color: '#00ff88',
                    lineWidth: 3,
                    priceFormat: {{ type: 'price', precision: 0 }},
                    title: 'Cumulative PnL',
                }});

                const rawData = {json.dumps(final_data)};
                debug.innerText = "Data nodes: " + rawData.length;

                if (rawData.length > 0) {{
                    series.setData(rawData);
                    
                    // Force multiple fit attempts to handle layout delays
                    const fit = () => chart.timeScale().fitContent();
                    fit();
                    setTimeout(fit, 100);
                    setTimeout(fit, 1000);
                }} else {{
                    container.innerHTML = "<div style='padding:100px; text-align:center;'>NO DATA FOUND IN CSV</div>";
                }}

                window.addEventListener('resize', () => {{
                    chart.applyOptions({{ 
                        width: container.clientWidth, 
                        height: container.clientHeight 
                    }});
                }});

            }} catch (e) {{
                container.innerHTML = "<div style='color:red; padding:20px;'>CHART ERROR: " + e.message + "</div>";
                console.error(e);
            }}
        }});
    </script>
</body>
</html>
"""
    output_path = r"C:\Users\user\.gemini\antigravity\brain\c31344a2-fc59-4a9d-bc24-28645bf47868\equity_viewer.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Equity Viewer Generated: {output_path}")

if __name__ == "__main__":
    generate_viewer()
