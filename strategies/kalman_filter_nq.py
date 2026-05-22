import databento as db
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Define the file path
data_file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"

print(f"Loading data from {data_file_path}...")

try:
    # Load the data
    store = db.DBNStore.from_file(data_file_path)
    df = store.to_df()
    
    print("Data loaded successfully.")
    
    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Slice the last 20,000 rows for performance to avoid plotly hanging
    slice_size = 20000
    if len(df) > slice_size:
        print(f"Data is too large, slicing the last {slice_size} records.")
        df_slice = df.tail(slice_size).copy()
    else:
        df_slice = df.copy()

    print("Applying Kalman Filter to Closing Prices...")
    
    # Basic 1D Kalman filter implementation
    sz = len(df_slice)
    prices = df_slice['close'].values

    # Tuning parameters
    Q = 1e-3  # process variance
    R = 1e-1  # estimate of measurement variance

    # Allocate arrays for results
    x_hat = np.zeros(sz)      # a posteriori estimate of x
    P = np.zeros(sz)          # a posteriori error estimate
    x_hat_minus = np.zeros(sz)# a priori estimate of x
    P_minus = np.zeros(sz)    # a priori error estimate
    K = np.zeros(sz)          # gain or blending factor

    # Initial guesses
    x_hat[0] = prices[0]
    P[0] = 1.0

    for k in range(1, sz):
        # Time update (Prediction)
        x_hat_minus[k] = x_hat[k-1]
        P_minus[k] = P[k-1] + Q

        # Measurement update (Correction)
        K[k] = P_minus[k] / (P_minus[k] + R)
        x_hat[k] = x_hat_minus[k] + K[k] * (prices[k] - x_hat_minus[k])
        P[k] = (1 - K[k]) * P_minus[k]

    df_slice['Kalman_Filter'] = x_hat

    print("Generating Professional Chart...")

    # Create subplots
    fig = go.Figure()

    # Original Price
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['close'], opacity=0.5, name='Original Close Price', line=dict(color='gray', width=1)))
    
    # Kalman Filter
    fig.add_trace(go.Scatter(x=df_slice.index, y=df_slice['Kalman_Filter'], opacity=0.9, name='Kalman Filter', line=dict(color='cyan', width=2)))

    # Candlestick can also be used if preferred, but line reduces visual clutter
    # If candlesticks are desired:
    # fig.add_trace(go.Candlestick(x=df_slice.index, open=df_slice['open'], high=df_slice['high'], low=df_slice['low'], close=df_slice['close'], name='OHLC', opacity=0.5))

    # Layout Updates for Professional Look
    fig.update_layout(
        template='plotly_dark', # Dark theme
        title=f'NQ 1m Price with Kalman Filter - Last {len(df_slice)} bars (Q={Q}, R={R})',
        xaxis_rangeslider_visible=False,
        height=800,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Update axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    # Save
    output_file = "nq_kalman_filter.html"
    fig.write_html(output_file)
    print(f"Chart saved to {os.path.abspath(output_file)}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"An error occurred: {e}")
