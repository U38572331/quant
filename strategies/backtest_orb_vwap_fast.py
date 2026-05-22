import struct
import datetime
import pandas as pd
import numpy as np
import os

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

def read_dbn_fast(file_path):
    print(f"Reading {file_path} using fast numpy loader...")
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"DBN\x01":
                raise ValueError("Not a DBN v1 file")
            
            meta_len = struct.unpack("<I", f.read(4))[0]
            f.read(meta_len) 
            
            dt = np.dtype([
                ('len_words', 'u1'), ('rtype', 'u1'), ('pub_id', '<u2'), ('inst_id', '<u4'), ('ts', '<u8'),
                ('open', '<i8'), ('high', '<i8'), ('low', '<i8'), ('close', '<i8'), ('volume', '<u8')
            ])
            
            raw_data = np.fromfile(f, dtype=dt)
            SCALE = 1e-9 
            
            df = pd.DataFrame({
                'Datetime': pd.to_datetime(raw_data['ts'], unit='ns', utc=True),
                'Open': raw_data['open'] * SCALE,
                'High': raw_data['high'] * SCALE,
                'Low': raw_data['low'] * SCALE,
                'Close': raw_data['close'] * SCALE,
                'Volume': raw_data['volume']
            })
            
            df = df[(df['High'] < 50000) & (df['Close'] > 2000) & (df['Low'] > 2000)]
            return df
    except Exception as e:
        print(f"Error: {e}")
        return None

def run_backtest(df):
    ORB_MINS = 60
    RR_LONG = 1.5
    RR_SHORT = 1.0 
    SL_STDEV_MULT = 1.0
    
    print("Preparing 5-Year Data...")
    df = df[df["Datetime"] >= "2021-01-01"].copy()
    df["DatetimeNY"] = df["Datetime"].dt.tz_convert("America/New_York")
    df["Time"] = df["DatetimeNY"].dt.time
    df["Date"] = df["DatetimeNY"].dt.date
    
    start_time = datetime.time(9, 30)
    end_time = datetime.time(16, 0)
    
    df_rth = df[(df["Time"] >= start_time) & (df["Time"] <= end_time)].copy()
    df_rth.sort_values("Datetime", inplace=True)
    
    trades = []
    grouped = df_rth.groupby("Date")
    print(f"Simulating {len(grouped)} sessions...")
    
    for d, day_df in grouped:
        hlc3 = (day_df["High"] + day_df["Low"] + day_df["Close"]) / 3.0
        pv = hlc3 * day_df["Volume"]
        cum_vol = day_df["Volume"].cumsum()
        vwap = pv.cumsum() / cum_vol
        stdev = np.sqrt((((hlc3**2)*day_df["Volume"]).cumsum() / cum_vol) - (vwap**2)).clip(lower=0)
        
        t_start = pd.Timestamp(datetime.datetime.combine(d, start_time)).tz_localize("America/New_York")
        t_orb_end = t_start + pd.Timedelta(minutes=ORB_MINS)
        
        orb_data = day_df[day_df["DatetimeNY"] < t_orb_end]
        if orb_data.empty: continue
        
        orb_high, orb_low = orb_data["High"].max(), orb_data["Low"].min()
        post_orb = day_df[day_df["DatetimeNY"] >= t_orb_end]
        if post_orb.empty: continue
        
        long_broken, short_broken, trade_taken = False, False, False
        
        for i in range(len(post_orb)):
            row = post_orb.iloc[i]
            if row["Close"] > orb_high: long_broken = True
            if row["Close"] < orb_low: short_broken = True
            
            if trade_taken: break
            
            # Entry Logic
            entry_type, limit_price, sl, tp = None, 0, 0, 0
            if long_broken and vwap.loc[row.name] > orb_low:
                entry_type, limit_price, sl = "Long", vwap.loc[row.name], orb_low
                tp = limit_price + (limit_price - sl) * RR_LONG
            elif short_broken and vwap.loc[row.name] < orb_high:
                entry_type, limit_price = "Short", vwap.loc[row.name]
                sl = limit_price + (stdev.loc[row.name] * SL_STDEV_MULT)
                tp = limit_price - (sl - limit_price) * RR_SHORT
            
            if entry_type and (limit_price - sl) != 0:
                # Check for fill in subsequent bars
                rem = post_orb.iloc[i+1:]
                fill_mask = (rem["Low"] <= limit_price) if entry_type == "Long" else (rem["High"] >= limit_price)
                fill_candidates = rem[fill_mask]
                
                if not fill_candidates.empty:
                    fill_bar = fill_candidates.iloc[0]
                    fill_idx = rem.index.get_loc(fill_bar.name)
                    entry_time = fill_bar["DatetimeNY"]
                    
                    # Exit Logic
                    after_fill = rem.iloc[fill_idx:] # Include fill bar for immediate hits
                    exit_p, exit_time, res = 0, None, "EOD"
                    
                    for _, b in after_fill.iterrows():
                        hit_sl = (b["Low"] <= sl) if entry_type == "Long" else (b["High"] >= sl)
                        hit_tp = (b["High"] >= tp) if entry_type == "Long" else (b["Low"] <= tp)
                        
                        if hit_sl:
                            exit_p, exit_time, res = sl, b["DatetimeNY"], "Loss"
                            break
                        if hit_tp:
                            exit_p, exit_time, res = tp, b["DatetimeNY"], "TP"
                            break
                        if b["Time"] >= datetime.time(15, 55):
                            exit_p, exit_time, res = b["Close"], b["DatetimeNY"], "EOD"
                            break
                    
                    if not exit_time:
                        last = after_fill.iloc[-1]
                        exit_p, exit_time, res = last["Close"], last["DatetimeNY"], "EOD"
                        
                    pnl = (exit_p - limit_price) if entry_type == "Long" else (limit_price - exit_p)
                    trades.append({"Date": d, "Type": entry_type, "Entry": limit_price, "Exit": exit_p, 
                                   "PnL": pnl, "Result": res, "EntryTime": entry_time, "ExitTime": exit_time})
                    trade_taken = True

    res_df = pd.DataFrame(trades)
    if not res_df.empty:
        res_df.to_csv("backtest_trades.csv", index=False)
        print(f"Success: {len(res_df)} trades. Total PnL: {res_df['PnL'].sum():.2f}")
    return res_df

if __name__ == "__main__":
    df = read_dbn_fast(r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn")
    if df is not None: run_backtest(df)
