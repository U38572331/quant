import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def main():
    print("Loading data...")
    df = pd.read_parquet(r"..\data\nq_pro.parquet", columns=['ts_event', 'symbol', 'high', 'low', 'close'])
    df = df[~df['symbol'].str.contains('-')].copy()
    df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')
    start_date = pd.Timestamp('2019-10-01', tz='America/New_York')
    df = df[df['ts_event'] >= start_date].copy()
    
    df['ny_date'] = df['ts_event'].dt.year * 10000 + df['ts_event'].dt.month * 100 + df['ts_event'].dt.day
    df['ny_time'] = df['ts_event'].dt.hour * 100 + df['ts_event'].dt.minute
    df = df[(df['ny_time'] >= 930) & (df['ny_time'] <= 1600)].reset_index(drop=True)
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    ny_date = df['ny_date'].values
    ny_time = df['ny_time'].values
    ts = df['ts_event'].values
    
    orb_mins = 15
    rr_long = 1.0
    rr_short = 1.0
    
    orb_end_time = 945
    
    position = 0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    orb_high = -1.0
    orb_low = 999999.0
    traded_today = False
    current_day = -1
    
    gross_loss = 0.0
    
    for i in range(10000): # Just first few days
        d = ny_date[i]
        t = ny_time[i]
        
        if d != current_day:
            current_day = d
            traded_today = False
            orb_high = -1.0
            orb_low = 999999.0
            if position != 0:
                print(f"End of day close at {ts[i]}")
                position = 0
        
        if 930 <= t < orb_end_time:
            if high[i] > orb_high: orb_high = high[i]
            if low[i] < orb_low: orb_low = low[i]
            
        if position != 0:
            if t >= 1555:
                pnl = (close[i] - entry_price) * position
                print(f"{ts[i]} 1555 Close. Pos: {position}, Entry: {entry_price}, Close: {close[i]}, PNL: {pnl}")
                if pnl < 0: gross_loss -= pnl
                position = 0
            else:
                hit_sl = False
                hit_tp = False
                if position == 1:
                    if low[i] <= stop_loss: hit_sl = True
                    if high[i] >= take_profit: hit_tp = True
                    
                    if hit_sl and hit_tp:
                        pnl = stop_loss - entry_price
                        print(f"{ts[i]} BOTH HIT. SL: {stop_loss}, TP: {take_profit}, H: {high[i]}, L: {low[i]}, PNL: {pnl}")
                        gross_loss -= pnl
                        position = 0
                    elif hit_sl:
                        pnl = stop_loss - entry_price
                        print(f"{ts[i]} SL HIT. SL: {stop_loss}, L: {low[i]}, PNL: {pnl}")
                        gross_loss -= pnl
                        position = 0
                    elif hit_tp:
                        pnl = take_profit - entry_price
                        print(f"{ts[i]} TP HIT. TP: {take_profit}, H: {high[i]}, PNL: {pnl}")
                        position = 0
                elif position == -1:
                    if high[i] >= stop_loss: hit_sl = True
                    if low[i] <= take_profit: hit_tp = True
                    if hit_sl and hit_tp:
                        pnl = entry_price - stop_loss
                        print(f"{ts[i]} BOTH HIT SHORT. PNL: {pnl}")
                        gross_loss -= pnl
                        position = 0
                    elif hit_sl:
                        pnl = entry_price - stop_loss
                        print(f"{ts[i]} SL HIT SHORT. PNL: {pnl}")
                        gross_loss -= pnl
                        position = 0
                    elif hit_tp:
                        pnl = entry_price - take_profit
                        print(f"{ts[i]} TP HIT SHORT. PNL: {pnl}")
                        position = 0

        if position == 0 and not traded_today and orb_high > 0 and t >= orb_end_time and t < 1555:
            if close[i] > orb_high:
                risk = close[i] - orb_low
                if risk > 0:
                    position = 1
                    entry_price = close[i]
                    stop_loss = orb_low
                    take_profit = close[i] + risk * rr_long
                    traded_today = True
                    print(f"{ts[i]} ENTER LONG. Price: {entry_price}, ORB: {orb_high}/{orb_low}, SL: {stop_loss}, TP: {take_profit}, Risk: {risk}")
            elif close[i] < orb_low:
                risk = orb_high - close[i]
                if risk > 0:
                    position = -1
                    entry_price = close[i]
                    stop_loss = orb_high
                    take_profit = close[i] - risk * rr_short
                    traded_today = True
                    print(f"{ts[i]} ENTER SHORT. Price: {entry_price}, ORB: {orb_high}/{orb_low}, SL: {stop_loss}, TP: {take_profit}, Risk: {risk}")

if __name__ == "__main__":
    main()
