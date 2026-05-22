import struct
import datetime
import pandas as pd
import numpy as np
import os

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

def calculate_val(day_df_up_to_now, tick_size=1.0):
    # Calculate volume profile by binning close prices
    bins = np.round(day_df_up_to_now['Close'] / tick_size) * tick_size
    vp = day_df_up_to_now.groupby(bins)['Volume'].sum()
    if vp.empty: return 0
    poc = vp.idxmax()
    total_vol = vp.sum()
    target_vol = total_vol * 0.70
    
    current_vol = vp.loc[poc]
    val = poc
    vah = poc
    
    vp = vp.sort_index()
    
    while current_vol < target_vol:
        lower_idx = val - tick_size
        upper_idx = vah + tick_size
        
        vol_lower = vp.get(lower_idx, 0)
        vol_upper = vp.get(upper_idx, 0)
        
        if vol_lower == 0 and vol_upper == 0:
            break
            
        if vol_lower > vol_upper:
            val = lower_idx
            current_vol += vol_lower
        elif vol_upper > vol_lower:
            vah = upper_idx
            current_vol += vol_upper
        else: # equal
            val = lower_idx
            vah = upper_idx
            current_vol += vol_lower + vol_upper
            
    return val

def run_backtest(df):
    ORB_MINS = 15
    TRADE_HOURS = 3.0
    RR_LONG = 3.0
    print("Preparing 5-Year Data...")
    df = df[df["Datetime"] >= "2021-01-01"].copy()
    df["DatetimeNY"] = df["Datetime"].dt.tz_convert("America/New_York")
    df["Time"] = df["DatetimeNY"].dt.time
    df["Date"] = df["DatetimeNY"].dt.date
    
    start_time = datetime.time(9, 30)
    end_time = datetime.time(16, 15)
    
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
        
        t_start = pd.Timestamp(datetime.datetime.combine(d, start_time)).tz_localize("America/New_York")
        t_orb_end = t_start + pd.Timedelta(minutes=ORB_MINS)
        t_trade_end = t_start + pd.Timedelta(hours=TRADE_HOURS)
        t_session_end = t_start.replace(hour=16, minute=0) # 16:00 open time is the end
        
        orb_data = day_df[day_df["DatetimeNY"] < t_orb_end]
        if orb_data.empty: continue
        
        orb_high = orb_data["High"].max()
        
        # Trade window logic
        post_orb = day_df[(day_df["DatetimeNY"] >= t_orb_end) & (day_df["DatetimeNY"] <= t_trade_end)]
        if post_orb.empty: continue
        
        signal_time = None
        
        # 5m close logic
        # A 5m candle closes every 5 minutes (09:49, 09:54, ...).
        # We can simulate this by looking at rows where minute % 5 == 4.
        for i, (idx, row) in enumerate(post_orb.iterrows()):
            if row["DatetimeNY"].minute % 5 == 4:
                if row["Close"] > orb_high:
                    signal_time = row["DatetimeNY"]
                    break
        
        if not signal_time:
            continue
            
        post_signal = day_df[(day_df["DatetimeNY"] > signal_time) & (day_df["DatetimeNY"] <= t_session_end)]
        if post_signal.empty: continue
        
        for i, (idx, row) in enumerate(post_signal.iterrows()):
            # Only enter if within trade window
            if row["DatetimeNY"] > t_trade_end:
                break
                
            current_vwap = vwap.loc[idx]
            
            # When price drops to or below VWAP, we enter long
            if row["Low"] <= current_vwap:
                # Assuming entry at exact VWAP (limit order)
                entry_price = current_vwap
                entry_time = row["DatetimeNY"]
                
                # Stop loss based on Session Volume Profile VAL
                df_up_to_now = day_df[day_df["DatetimeNY"] <= entry_time]
                val = calculate_val(df_up_to_now, tick_size=1.0)
                sl = val
                
                if sl >= entry_price:
                    # Invalid risk setup
                    break
                    
                tp = entry_price + (entry_price - sl) * RR_LONG
                
                # Check for fill in subsequent bars
                rem = day_df.loc[idx:] # include current bar because it might hit SL/TP in same bar
                
                exit_p = 0
                exit_time = None
                res = "EOD"
                
                for _, b in rem.iterrows():
                    # Check SL then TP
                    if b["Low"] <= sl:
                        exit_p = sl
                        exit_time = b["DatetimeNY"]
                        res = "Loss"
                        break
                    if b["High"] >= tp:
                        exit_p = tp
                        exit_time = b["DatetimeNY"]
                        res = "Win"
                        break
                    
                    # 16:00 close 
                    if b["Time"] >= datetime.time(16, 0): 
                        exit_p = b["Close"]
                        exit_time = b["DatetimeNY"]
                        res = "EOD"
                        break
                        
                if not exit_time: 
                    last = rem.iloc[-1]
                    exit_p = last["Close"]
                    exit_time = last["DatetimeNY"]
                    res = "EOD"
                    
                pnl = exit_p - entry_price
                trades.append({
                    "Date": d,
                    "Type": "Long",
                    "Entry": entry_price,
                    "SL": sl,
                    "TP": tp,
                    "Exit": exit_p,
                    "PnL": pnl,
                    "Result": res,
                    "EntryTime": entry_time,
                    "ExitTime": exit_time
                })
                break # 1 trade per session
                
    res_df = pd.DataFrame(trades)
    if not res_df.empty:
        os.makedirs(r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest", exist_ok=True)
        out_path = r"C:\Users\user\.gemini\antigravity\scratch\nq_orb_backtest\backtest_15m_orb_trades.csv"
        res_df.to_csv(out_path, index=False)
        print(f"Success: {len(res_df)} trades. Total PnL: {res_df['PnL'].sum():.2f}")
        
        wins = res_df[res_df['Result'] == 'Win']
        losses = res_df[res_df['Result'] == 'Loss']
        eod = res_df[res_df['Result'] == 'EOD']
        win_rate = len(wins) / len(res_df) if len(res_df) > 0 else 0
        print(f"Wins: {len(wins)}, Losses: {len(losses)}, EOD closed: {len(eod)}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Average PnL per trade: {res_df['PnL'].mean():.2f}")
        print(f"Results saved to {out_path}")
    else:
        print("No trades taken.")
        
    return res_df

if __name__ == "__main__":
    file_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
    df = read_dbn_fast(file_path)
    if df is not None:
        run_backtest(df)
