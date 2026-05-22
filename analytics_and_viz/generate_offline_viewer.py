import pandas as pd
import plotly.graph_objects as go
import os

def generate_offline_viewer():
    trades_path = "backtest_trades.csv"
    if not os.path.exists(trades_path):
        return
        
    df = pd.read_csv(trades_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['CumPnL'] = df['PnL'].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['CumPnL'],
        name="Equity",
        line=dict(color="#00ff88", width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 136, 0.1)'
    ))

    fig.update_layout(
        template="plotly_dark",
        title="NQ STRATEGY EQUITY (OFFLINE VIEWER)",
        xaxis=dict(rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title="PnL Points"),
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#0a0a0a",
        height=800
    )

    output_path = r"C:\Users\user\.gemini\antigravity\brain\c31344a2-fc59-4a9d-bc24-28645bf47868\equity_final_viewer.html"
    # include_plotlyjs=True inlines the entire 3MB library into the file
    fig.write_html(output_path, include_plotlyjs=True)
    print(f"Offline Viewer Generated: {output_path}")

if __name__ == "__main__":
    generate_offline_viewer()
