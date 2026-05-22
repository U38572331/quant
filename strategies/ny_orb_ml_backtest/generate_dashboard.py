import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def calculate_drawdown(equity_series):
    peak = equity_series.expanding(min_periods=1).max()
    drawdown = equity_series - peak
    return drawdown

def run_monte_carlo(trades, num_simulations=100, num_trades=500):
    paths = np.zeros((num_simulations, num_trades + 1))
    paths[:, 0] = 100000 # Starting capital
    for i in range(num_simulations):
        sampled_trades = np.random.choice(trades, size=num_trades, replace=True)
        paths[i, 1:] = 100000 + np.cumsum(sampled_trades)
    return paths

def main():
    print("Generating Professional Dashboard...")
    
    # Load data
    df_all = pd.read_csv("ml_trades_output.csv")
    df_filtered = pd.read_csv("ml_trades_filtered.csv")
    
    # Metrics
    base_trades = len(df_all)
    base_wr = (df_all['pnl'] > 0).mean()
    base_pnl = df_all['pnl'].sum()
    
    ml_trades = len(df_filtered)
    ml_wr = (df_filtered['pnl'] > 0).mean()
    ml_pnl = df_filtered['pnl'].sum()
    gross_win = df_filtered[df_filtered['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_filtered[df_filtered['pnl'] < 0]['pnl'].sum())
    ml_pf = gross_win / gross_loss if gross_loss > 0 else 999.0
    
    # Equity Curves
    df_all['cumulative_pnl'] = df_all['pnl'].cumsum() + 100000
    df_filtered['cumulative_pnl'] = df_filtered['pnl'].cumsum() + 100000
    
    # Drawdown
    df_filtered['drawdown'] = calculate_drawdown(df_filtered['cumulative_pnl'])
    
    # Plotly Subplots
    fig = make_subplots(
        rows=3, cols=2,
        specs=[[{"colspan": 2}, None],
               [{}, {}],
               [{"colspan": 2}, None]],
        subplot_titles=("Strategy Equity Curve: Base vs ML Filtered", 
                        "Drawdown Distribution", "Monte Carlo Simulation (100 paths)",
                        "Trade PNL Distribution")
    )
    
    # 1. Equity Curve
    fig.add_trace(go.Scatter(x=df_all.index, y=df_all['cumulative_pnl'], name='Base Strategy', line=dict(color='gray', dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_filtered.index, y=df_filtered['cumulative_pnl'], name='ML Filtered', line=dict(color='#00ff88', width=2)), row=1, col=1)
    
    # 2. Drawdown Distribution (Histogram)
    dd_vals = df_filtered[df_filtered['drawdown'] < 0]['drawdown']
    fig.add_trace(go.Histogram(x=dd_vals, name='Drawdowns', marker_color='#ff3366', nbinsx=30), row=2, col=1)
    
    # 3. Monte Carlo
    mc_paths = run_monte_carlo(df_filtered['pnl'].values)
    for i in range(mc_paths.shape[0]):
        fig.add_trace(go.Scatter(y=mc_paths[i], mode='lines', line=dict(color='rgba(0, 255, 136, 0.05)'), showlegend=False), row=2, col=2)
    fig.add_trace(go.Scatter(y=mc_paths.mean(axis=0), name='Expected MC Path', line=dict(color='#00ff88', width=2)), row=2, col=2)
    
    # 4. Trade PNL Distribution
    fig.add_trace(go.Histogram(x=df_filtered['pnl'], name='PNL', marker_color='#33ccff', nbinsx=50), row=3, col=1)
    
    # Layout styling for modern dark mode web app
    fig.update_layout(
        template='plotly_dark',
        height=1000,
        title_text="NQ ORB Strategy with Machine Learning Filter - Performance Dashboard",
        title_x=0.5,
        title_font=dict(size=24, color='#ffffff', family='Inter'),
        plot_bgcolor='#111111',
        paper_bgcolor='#0a0a0a',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Generate Plotly HTML
    plotly_html = fig.to_html(full_html=True, include_plotlyjs='cdn')
    
    # Custom CSS and Metrics HTML
    custom_html = f"""
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0a0a0a;
            color: #ffffff;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            background: linear-gradient(90deg, #00ff88, #00ccff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{
            text-align: center;
            color: #888888;
            margin-bottom: 3rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}
        .metric-card {{
            background-color: #111111;
            border: 1px solid #222222;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-5px);
            border-color: #00ff88;
        }}
        .metric-title {{
            font-size: 0.9rem;
            color: #888888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .positive {{ color: #00ff88; }}
        .chart-container {{
            background-color: #111111;
            border-radius: 16px;
            padding: 1rem;
            border: 1px solid #222222;
        }}
    </style>
    <h1>NQ ORB Quantitative Engine</h1>
    <div class="subtitle">AI-Filtered Breakout Strategy</div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">Total Trades</div>
            <div class="metric-value">{ml_trades}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Win Rate</div>
            <div class="metric-value positive">{ml_wr*100:.1f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Profit Factor</div>
            <div class="metric-value positive">{ml_pf:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Net Profit (Pts)</div>
            <div class="metric-value positive">{ml_pnl:.1f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Base Strategy WR</div>
            <div class="metric-value" style="color: #ff3366;">{base_wr*100:.1f}%</div>
        </div>
    </div>
    """
    
    # Insert custom HTML right after <body>
    html_content = plotly_html.replace('<body>', f'<body>\n{custom_html}')
    
    with open("dashboard.html", "w", encoding='utf-8') as f:
        f.write(html_content)
        
    print("Dashboard created at dashboard.html")

if __name__ == "__main__":
    main()
