import databento as db
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import time

# Constants
FILE_PATH = r"C:\Users\user\Downloads\GLBX-20260503-3DDYMET438\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn\glbx-mdp3-20160403-20260502.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\databento_analysis"
ORB_MINUTES = 30
RR_RATIO = 1.0
TIMEFRAME = '5min'

def run_backtest():
    print("Loading data...")
    store = db.DBNStore.from_file(FILE_PATH)
    df_raw = store.to_df()
    
    # 1. Pre-process: Clean data and handle New York timezone
    print("Converting to New York time and cleaning...")
    df_raw = df_raw.reset_index()
    df_raw['ts_event'] = df_raw['ts_event'].dt.tz_convert('America/New_York')
    
    # 2. Backtest Logic (Daily loop with per-day symbol selection)
    print("Running backtest loop...")
    trades = []
    
    # Get unique dates
    unique_dates = df_raw['ts_event'].dt.date.unique()
    
    for date in unique_dates:
        # Get all data for this day
        day_raw = df_raw[df_raw['ts_event'].dt.date == date]
        if day_raw.empty:
            continue
            
        # Select the most liquid symbol for this day (to avoid price jumps between contracts)
        top_symbol = day_raw.groupby('symbol')['volume'].sum().idxmax()
        day_data_1m = day_raw[day_raw['symbol'] == top_symbol].set_index('ts_event').sort_index()
        
        # Resample to 5m for this symbol
        day_data_5m = day_data_1m.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if day_data_5m.empty:
            continue
            
        # Define session times
        orb_start = pd.to_datetime(f"{date} 09:30:00").tz_localize('America/New_York', ambiguous='NaT', nonexistent='shift_forward')
        orb_end = orb_start + pd.Timedelta(minutes=ORB_MINUTES)
        market_close = pd.to_datetime(f"{date} 15:55:00").tz_localize('America/New_York', ambiguous='NaT', nonexistent='shift_forward')
        
        # Get ORB range
        orb_data = day_data_5m[(day_data_5m.index >= orb_start) & (day_data_5m.index < orb_end)]
        if orb_data.empty:
            continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        
        # Strategy variables
        entry_price = None
        stop_loss = orb_low
        take_profit = None
        traded_today = False
        
        # Iterate through bars after ORB
        trading_data = day_data_5m[day_data_5m.index >= orb_end]
        
        for ts, bar in trading_data.iterrows():
            # Mandatory exit at 15:55
            if ts >= market_close:
                if entry_price is not None:
                    # Exit at close
                    exit_price = bar['close']
                    profit = exit_price - entry_price
                    trades.append({'date': date, 'entry_ts': entry_ts, 'exit_ts': ts, 'entry': entry_price, 'exit': exit_price, 'profit': profit, 'type': 'EOD'})
                    entry_price = None
                break
            
            # Check for Entry (if not in position and haven't traded today)
            if entry_price is None and not traded_today:
                if bar['close'] > orb_high:
                    entry_price = bar['close']
                    entry_ts = ts
                    risk = entry_price - stop_loss
                    if risk <= 0: # Invalid risk
                        entry_price = None
                        continue
                    take_profit = entry_price + (risk * RR_RATIO)
                    traded_today = True
                    continue # Moved into position
            
            # Check for Exit (if in position)
            if entry_price is not None:
                # Check Stop Loss (using bar low)
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                    profit = exit_price - entry_price
                    trades.append({'date': date, 'entry_ts': entry_ts, 'exit_ts': ts, 'entry': entry_price, 'exit': exit_price, 'profit': profit, 'type': 'SL'})
                    entry_price = None
                # Check Take Profit (using bar high)
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                    profit = exit_price - entry_price
                    trades.append({'date': date, 'entry_ts': entry_ts, 'exit_ts': ts, 'entry': entry_price, 'exit': exit_price, 'profit': profit, 'type': 'TP'})
                    entry_price = None

    # 4. Results
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("No trades found.")
        return

    trades_df['cum_profit'] = trades_df['profit'].cumsum()
    
    # Statistics
    total_trades = len(trades_df)
    win_rate = (trades_df['profit'] > 0).sum() / total_trades
    avg_profit = trades_df['profit'].mean()
    total_profit = trades_df['profit'].sum()
    profit_factor = trades_df[trades_df['profit'] > 0]['profit'].sum() / abs(trades_df[trades_df['profit'] < 0]['profit'].sum())
    
    print("\n--- Performance Summary ---")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Total Profit (Points): {total_profit:.2f}")
    print(f"Avg Profit (Points): {avg_profit:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    # Save results
    trades_df.to_csv(os.path.join(OUTPUT_DIR, "trades_log.csv"), index=False)
    
    # Plot Equity Curve
    plt.figure(figsize=(12, 6))
    plt.plot(trades_df['date'], trades_df['cum_profit'], label='Cumulative Profit (Points)')
    plt.title(f'ORB Breakout Strategy - Cumulative Profit\n(30m ORB, 1:1 RR, {TIMEFRAME} Timeframe)')
    plt.xlabel('Date')
    plt.ylabel('Profit (Points)')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "equity_curve.png"))
    print(f"Equity curve saved to equity_curve.png")

if __name__ == "__main__":
    run_backtest()
