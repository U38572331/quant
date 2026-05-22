import pandas as pd
import plotly.graph_objects as go
import os
import traceback

# Define file paths
csv_path = r"C:\Users\user\Documents\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
output_file = "ohlcv_chart_5m.html"

def create_chart():
    print(f"Reading data from {csv_path}...")
    try:
        # Read CSV without headers
        # Columns deduced: Time, ?, ?, Volume, Open, High, Low, Close, ?, Symbol
        # Read CSV without headers
        # Columns deduced: Time, ?, ?, Volume, Open, High, Low, Close, ?, Symbol
        df = pd.read_csv(csv_path, header=None, on_bad_lines='warn')
        print("Data loaded. Head:")
        print(df.head())
        print(df.dtypes)
        
        # Rename columns for easier access
        df.rename(columns={
            0: 'Time',
            3: 'Volume',
            4: 'Open',
            5: 'High',
            6: 'Low',
            7: 'Close',
            9: 'Symbol'
        }, inplace=True)
        
        # Convert Time to datetime objects
        print("Converting Time column to datetime...")
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        
        # Drop rows with invalid time
        if df['Time'].isna().any():
            print(f"Dropping {df['Time'].isna().sum()} rows with invalid time.")
            df.dropna(subset=['Time'], inplace=True)

        # Ensure numeric columns
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with invalid numeric data
        if df[numeric_cols].isna().any().any():
             print("Dropping rows with non-numeric data in OHLCV columns.")
             df.dropna(subset=numeric_cols, inplace=True)

        # Resample to 5-minute intervals
        print("Resampling to 5-minute intervals...")
        df.set_index('Time', inplace=True)
        
        df_5m = df.resample('5min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum',
            'Symbol': 'first' # Keep symbol
        })
        
        # Drop rows with NaN (periods with no data)
        df_5m.dropna(inplace=True)
        df_5m.reset_index(inplace=True)

        print(f"5-minute data size: {len(df_5m)}")

        # Update df_plot to be the 5m data
        dataset_size = len(df_5m)
        plot_rows = 2000 # 5000 5m bars is quite a lot of time
        if dataset_size > plot_rows:
            print(f"Dataset is large. Plotting the last {plot_rows} 5-minute candles.")
            df_plot = df_5m.tail(plot_rows).copy()
        else:
            df_plot = df_5m.copy()

        print("Generating 5-minute candlestick chart...")
        fig = go.Figure(data=[go.Candlestick(x=df_plot['Time'],
                        open=df_plot['Open'],
                        high=df_plot['High'],
                        low=df_plot['Low'],
                        close=df_plot['Close'],
                        name='OHLC')])

        fig.update_layout(
            title=f'OHLCV Chart (5-Minute) - Last {plot_rows} bars',
            yaxis_title='Price',
            xaxis_title='Time',
            xaxis_rangeslider_visible=True
        )

        fig.write_html(output_file)
        print(f"Chart saved to {os.path.abspath(output_file)}")

    except Exception as e:
        traceback.print_exc()
        print(f"Error creating chart: {e}")

if __name__ == "__main__":
    create_chart()
