import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def generate_advanced_report():
    file_path = r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\backtest_15m_orb_trades.csv"
    if not os.path.exists(file_path):
        print("Trades file not found.")
        return
        
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    df['EntryTime'] = pd.to_datetime(df['EntryTime'], utc=True)
    df['ExitTime'] = pd.to_datetime(df['ExitTime'], utc=True)
    df['Duration_Mins'] = (df['ExitTime'] - df['EntryTime']).dt.total_seconds() / 60.0
    
    df['Cumulative_PnL'] = df['PnL'].cumsum()
    df['HighWaterMark'] = df['Cumulative_PnL'].cummax()
    df['Drawdown'] = df['Cumulative_PnL'] - df['HighWaterMark']
    
    # KPIs Calculation
    total_trades = len(df)
    total_pnl = df['PnL'].sum()
    wins = df[df['PnL'] > 0]
    losses = df[df['PnL'] < 0]
    
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    gross_profit = wins['PnL'].sum()
    gross_loss = abs(losses['PnL'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    avg_win = wins['PnL'].mean() if len(wins) > 0 else 0
    avg_loss = abs(losses['PnL'].mean()) if len(losses) > 0 else 0
    payoff_ratio = avg_win / avg_loss if avg_loss != 0 else float('inf')
    expectancy = df['PnL'].mean()
    max_dd = abs(df['Drawdown'].min())
    
    # Daily metrics for Sharpe/Sortino
    daily_pnl = df.groupby('Date')['PnL'].sum()
    mean_daily = daily_pnl.mean()
    std_daily = daily_pnl.std()
    sharpe = (mean_daily / std_daily) * np.sqrt(252) if std_daily != 0 else 0
    
    downside = daily_pnl[daily_pnl < 0]
    sortino = (mean_daily / downside.std()) * np.sqrt(252) if downside.std() != 0 else 0
    
    # Create Layout
    fig = make_subplots(
        rows=5, cols=2,
        specs=[
            [{"type": "domain"}, {"type": "domain"}],      # Row 1: KPI Indicators
            [{"colspan": 2}, None],                        # Row 2: Equity Curve
            [{"colspan": 2}, None],                        # Row 3: Drawdown Curve
            [{"type": "heatmap"}, {"type": "bar"}],      # Row 4: Heatmap & Yearly Bar
            [{"type": "histogram"}, {"type": "histogram"}] # Row 5: PnL Dist & Duration Dist
        ],
        subplot_titles=(
            "KPIs: Win Rate & Profit Factor", "KPIs: Sharpe & Max Drawdown",
            "Cumulative Equity Curve", 
            "Drawdown (Points)",
            "Monthly Returns Heatmap", "Yearly Returns",
            "Trade PnL Distribution", "Trade Duration Distribution (Minutes)"
        ),
        vertical_spacing=0.08,
        row_heights=[0.1, 0.25, 0.15, 0.25, 0.25]
    )
    
    # Row 1: KPIs
    fig.add_trace(go.Indicator(
        mode="number+gauge", value=win_rate * 100, number={'suffix': "%", 'valueformat': '.1f'},
        title={'text': f"Win Rate<br><span style='font-size:0.8em;color:gray'>Profit Factor: {profit_factor:.2f}</span>"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#00ffcc"}},
        domain={'row': 0, 'column': 0}
    ), row=1, col=1)
    
    fig.add_trace(go.Indicator(
        mode="number", value=sharpe, number={'valueformat': '.2f'},
        title={'text': f"Sharpe Ratio<br><span style='font-size:0.8em;color:gray'>Sortino: {sortino:.2f} | Max DD: {max_dd:.0f} pts</span>"},
        domain={'row': 0, 'column': 1}
    ), row=1, col=2)
    
    # Row 2: Equity
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Cumulative_PnL'], mode='lines', name='Equity',
        line=dict(color='#00ffcc', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.1)'
    ), row=2, col=1)
    
    # Row 3: Drawdown
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Drawdown'], mode='lines', name='Drawdown',
        line=dict(color='#ff3366', width=1), fill='tozeroy', fillcolor='rgba(255, 51, 102, 0.3)'
    ), row=3, col=1)
    
    # Row 4: Monthly Heatmap & Yearly Bar
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    monthly_pnl = df.groupby(['Year', 'Month'])['PnL'].sum().reset_index()
    monthly_pivot = monthly_pnl.pivot(index='Year', columns='Month', values='PnL').fillna(0)
    for m in range(1, 13):
        if m not in monthly_pivot.columns: monthly_pivot[m] = 0
    monthly_pivot = monthly_pivot.reindex(columns=range(1, 13))
    
    fig.add_trace(go.Heatmap(
        z=monthly_pivot.values, x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        y=monthly_pivot.index, colorscale='RdYlGn', zmid=0, text=np.round(monthly_pivot.values, 0),
        texttemplate="%{text}", textfont={"size": 10}, showscale=False
    ), row=4, col=1)
    
    yearly_pnl = df.groupby('Year')['PnL'].sum().reset_index()
    fig.add_trace(go.Bar(
        x=yearly_pnl['Year'], y=yearly_pnl['PnL'],
        marker_color=['#00ffcc' if val > 0 else '#ff3366' for val in yearly_pnl['PnL']],
        name='Yearly PnL', text=np.round(yearly_pnl['PnL'], 0), textposition='auto'
    ), row=4, col=2)
    
    # Row 5: Distributions
    fig.add_trace(go.Histogram(
        x=df['PnL'], nbinsx=50, marker_color='#3399ff', name='PnL Dist'
    ), row=5, col=1)
    
    fig.add_trace(go.Histogram(
        x=df['Duration_Mins'], nbinsx=50, marker_color='#9933ff', name='Duration Dist'
    ), row=5, col=2)
    
    # Layout finalize
    fig.update_layout(
        title="Institutional-Grade Quant Dashboard | NQ ORB Strategy",
        template="plotly_dark", height=1600, showlegend=False,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    out_file = r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\Advanced_Quant_Report.html"
    fig.write_html(out_file)
    print(f"Generated successfully: {out_file}")
    
    # Also write a markdown file with raw metrics
    md_content = f"""# Advanced Quantitative Metrics
    
### Core Performance
- **Total Net Profit**: {total_pnl:.2f} points
- **Gross Profit**: {gross_profit:.2f} points
- **Gross Loss**: {gross_loss:.2f} points
- **Profit Factor**: {profit_factor:.3f}
- **Total Trades**: {total_trades}
- **Win Rate**: {win_rate*100:.2f}%

### Risk & Reward
- **Max Drawdown**: {max_dd:.2f} points
- **Average Win**: {avg_win:.2f} points
- **Average Loss**: {avg_loss:.2f} points
- **Payoff Ratio (Avg Win / Avg Loss)**: {payoff_ratio:.3f}
- **Expectancy (Avg PnL per Trade)**: {expectancy:.2f} points

### Risk-Adjusted Returns
- **Annualized Sharpe Ratio**: {sharpe:.3f}
- **Annualized Sortino Ratio**: {sortino:.3f}
"""
    with open(r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\Quant_Metrics_Summary.md", "w", encoding="utf-8") as text_file:
        text_file.write(md_content)

if __name__ == "__main__":
    generate_advanced_report()
