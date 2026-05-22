import databento as db
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Define the file path
data_file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

print(f"Loading data from {data_file_path}...")

try:
    # Load the data
    store = db.DBNStore.from_file(data_file_path)
    # Using iterator for large files if needed, but for < 10GB RAM systems, reading full might be tight.
    # NQ 1m for 15 years is manageable in memory (approx 500MB - 1GB).
    df = store.to_df()
    
    print("Data loaded successfully.")
    
    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Calculate Volume Moving Average (optional) or just Price MAs
    # Calculate Price Moving Averages
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA60'] = df['close'].rolling(window=60).mean()

    # Slice the last 20,000 rows for performance
    slice_size = 20000
    if len(df) > slice_size:
        print(f"Data is too large, slicing the last {slice_size} records.")
        df_slice = df.tail(slice_size)
    else:
        df_slice = df

    print("Generating Professional Chart...")

    # Create subplots: Row 1 for Price/MA, Row 2 for Volume
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('NQ Price', 'Volume'),
                        row_heights=[0.7, 0.3])

    # 1. Candlestick
    fig.add_trace(go.Candlestick(x=df_slice.index,
                                 open=df_slice['open'],
                                 high=df_slice['high'],
                                 low=df_slice['low'],
                                 close=df_slice['close'],
                                 name='OHLC'), 
                  row=1, col=1)

    # 2. Moving Averages
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MA5'], opacity=0.7, line=dict(color='cyan', width=1), name='MA 5'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MA20'], opacity=0.7, line=dict(color='yellow', width=1), name='MA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['MA60'], opacity=0.7, line=dict(color='purple', width=1), name='MA 60'), row=1, col=1)

    # 3. Volume
    # Color volume bars based on price change
    colors = ['green' if row['close'] >= row['open'] else 'red' for index, row in df_slice.iterrows()]
    fig.add_trace(go.Bar(x=df_slice.index, y=df_slice['volume'], marker_color=colors, name='Volume'), row=2, col=1)

    # Layout Updates for Professional Look
    fig.update_layout(
        template='plotly_dark', # Dark theme
        title=f'NQ 1m Professional Chart - Last {len(df_slice)} bars',
        xaxis_rangeslider_visible=False, # Disable range slider on top plot
        height=800,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Update axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    # Save
    output_file = "nq_chart_pro.html"
    fig.write_html(output_file)
    print(f"Professional chart saved to {os.path.abspath(output_file)}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"An error occurred: {e}")
