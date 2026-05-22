import pandas as pd
import plotly.graph_objects as go
import os

def generate_plotly_viewer():
    trades_path = "backtest_trades.csv"
    if not os.path.exists(trades_path):
        print("Trades file not found.")
        return
        
    df = pd.read_csv(trades_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['CumPnL'] = df['PnL'].cumsum()

    # Create Plotly Figure
    fig = go.Figure()

    # Add Equity Curve
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['CumPnL'],
        name="Equity",
        line=dict(color="#00ff88", width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 136, 0.1)'
    ))

    # Add Range Slider & Selectors for ultimate zoomability
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="NQ ORB + VWAP | Interactive PnL History (Zoomable)",
            font=dict(size=24, color="#00ff88")
        ),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ]),
                font=dict(color="#000")
            ),
            rangeslider=dict(visible=True),
            type="date"
        ),
        yaxis=dict(title="PnL Points", gridcolor="#333"),
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#0a0a0a",
        height=800
    )

    output_path = r"C:\Users\user\.gemini\antigravity\brain\c31344a2-fc59-4a9d-bc24-28645bf47868\equity_history_viewer.html"
    fig.write_html(output_path, include_plotlyjs='cdn')
    print(f"Plotly Viewer Generated: {output_path}")

if __name__ == "__main__":
    generate_plotly_viewer()
