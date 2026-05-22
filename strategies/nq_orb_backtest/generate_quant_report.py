import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os

def generate_report():
    file_path = r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\backtest_15m_orb_trades.csv"
    if not os.path.exists(file_path):
        print("Trades file not found.")
        return
        
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Cumulative_PnL'] = df['PnL'].cumsum()
    df['HighWaterMark'] = df['Cumulative_PnL'].cummax()
    df['Drawdown'] = df['Cumulative_PnL'] - df['HighWaterMark']
    
    # Set up the dashboard
    fig = make_subplots(
        rows=3, cols=2,
        specs=[
            [{"colspan": 2}, None], # Equity Curve spans both columns
            [{"colspan": 2}, None], # Drawdown spans both columns
            [{"type": "heatmap"}, {"type": "pie"}] # Heatmap and Pie chart
        ],
        subplot_titles=(
            "Cumulative PnL (Equity Curve)", 
            "Drawdown", 
            "Monthly Returns (Points)", 
            "Trade Outcomes"
        ),
        vertical_spacing=0.1,
        row_heights=[0.4, 0.2, 0.4]
    )
    
    # 1. Equity Curve
    fig.add_trace(
        go.Scatter(
            x=df['Date'], y=df['Cumulative_PnL'],
            mode='lines', name='Cumulative PnL',
            line=dict(color='#00ffcc', width=2),
            fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.1)'
        ),
        row=1, col=1
    )
    
    # 2. Drawdown
    fig.add_trace(
        go.Scatter(
            x=df['Date'], y=df['Drawdown'],
            mode='lines', name='Drawdown',
            line=dict(color='#ff3366', width=1),
            fill='tozeroy', fillcolor='rgba(255, 51, 102, 0.3)'
        ),
        row=2, col=1
    )
    
    # 3. Monthly Returns Heatmap
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    monthly_pnl = df.groupby(['Year', 'Month'])['PnL'].sum().reset_index()
    monthly_pivot = monthly_pnl.pivot(index='Year', columns='Month', values='PnL').fillna(0)
    
    # Ensure all 12 months are in columns for consistent heatmap
    for m in range(1, 13):
        if m not in monthly_pivot.columns:
            monthly_pivot[m] = 0
    monthly_pivot = monthly_pivot.reindex(columns=range(1, 13))
    
    fig.add_trace(
        go.Heatmap(
            z=monthly_pivot.values,
            x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            y=monthly_pivot.index,
            colorscale='RdYlGn',
            zmid=0,
            text=np.round(monthly_pivot.values, 0),
            texttemplate="%{text}",
            textfont={"size":10},
            showscale=False
        ),
        row=3, col=1
    )
    
    # 4. Win/Loss Pie Chart
    results_counts = df['Result'].value_counts()
    colors={'Win': '#00ffcc', 'Loss': '#ff3366', 'EOD': '#888888'}
    pie_colors = [colors.get(x, '#333333') for x in results_counts.index]
    
    fig.add_trace(
        go.Pie(
            labels=results_counts.index, 
            values=results_counts.values,
            hole=0.4,
            marker_colors=pie_colors,
            textinfo='label+percent'
        ),
        row=3, col=2
    )
    
    # Finalize Layout
    fig.update_layout(
        title="NQ 15m ORB VWAP Strategy Quantitative Performance",
        title_font_size=24,
        template="plotly_dark",
        height=1000,
        showlegend=False,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    fig.update_yaxes(title_text="Points", row=1, col=1)
    fig.update_yaxes(title_text="Points", row=2, col=1)
    
    out_file = r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\Quant_Report.html"
    fig.write_html(out_file)
    print(f"Professional Dashboard generated at: {out_file}")

if __name__ == "__main__":
    generate_report()
