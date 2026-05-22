import struct
import datetime
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------
# 1. DBN Parsing Logic (Manual)
# ---------------------------------------------------------
def read_dbn_file(file_path):
    """
    Reads a DBN OHLCV-1m file manually.
    Returns a DataFrame.
    """
    data_list = []
    
    # Metadata/constants
    # Price scale 1e-6 based on inspection
    PRICE_SCALE = 1e-9 
    # Wait, previous inspection: 1831750000 -> 1831.75.
    # 1831.75 * 1e6 = 1,831,750,000.
    # So raw / 1e6 = price.
    PRICE_SCALE = 1e-9 * 1000 # 1e-6
    # Actually, verify exact scale.
    # If standard databento is 1e-9?
    # 1831750000 * 1e-9 = 1.83. Wrong.
    # 1831750000 * 1e-6 = 1831.75. Correct.
    SCALE = 1e-6
    
    print(f"Reading {file_path}...")
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"DBN\x01":
                raise ValueError("Not a DBN v1 file")
            
            meta_len = struct.unpack("<I", f.read(4))[0]
            f.read(meta_len) # Skip metadata
            
            # Read all remaining data
            # Reading in chunks is better for memory, but for 250MB file, read all is fine.
            # However, `read()` might be safer in chunks if file is huge.
            # We already know record size is 56 bytes.
            
            # Efficient reading:
            # We can use numpy frombuffer if we handle the struct alignment?
            # But the struct has mixed types (u8, u16, u32, u64, i64).
            # Iterative struct unpacking is slow in pure Python.
            # But 5M rows... might take a minute. Acceptable.
            
            BATCH_SIZE = 100000
            RECORD_SIZE = 56
            
            while True:
                batch = f.read(BATCH_SIZE * RECORD_SIZE)
                if not batch:
                    break
                
                # We can iterate over this buffer
                num_records = len(batch) // RECORD_SIZE
                for i in range(num_records):
                    offset = i * RECORD_SIZE
                    # Parse interesting fields
                    # Hdr: 16b. TS is at offset 8 (u64).
                    # Payload start 16.
                    # Open(0), High(8), Low(16), Close(24), Vol(32) relative to payload
                    
                    # Unpack TS (u64 at 8-16) and OHLCV (i64*4 + u64 at 16-56)
                    # Total 56 bytes.
                    
                    # Optimized unpack?
                    # Format: 8x (skip len/rtype/pub/inst) Q q q q q Q
                    # Wait, struct format must match exactly.
                    # <BBHIQ qqqqQ
                    # < x x 2x 4x Q q q q q Q  (using padding x)
                    # B(1)+B(1)+H(2)+I(4)=8 bytes. So 8x works to skip to TS.
                    
                    record_data = struct.unpack_from("<8xQqqqqQ", batch, offset)
                    
                    ts = record_data[0]
                    o = record_data[1] * SCALE
                    h = record_data[2] * SCALE
                    l = record_data[3] * SCALE
                    c = record_data[4] * SCALE
                    v = record_data[5]
                    
                    data_list.append((ts, o, h, l, c, v))
                    
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    print(f"Parsed {len(data_list)} records.")
    df = pd.DataFrame(data_list, columns=["ts_raw", "Open", "High", "Low", "Close", "Volume"])
    df["Datetime"] = pd.to_datetime(df["ts_raw"], unit="ns", utc=True)
    df.drop(columns=["ts_raw"], inplace=True)
    return df

# ---------------------------------------------------------
# 2. Backtest Engine
# ---------------------------------------------------------
def run_backtest(df):
    # Parameters
    ORB_MINS = 60
    RR_LONG = 1.5
    RR_SHORT = 0.5
    SL_STDEV_MULT = 1.0
    
    print("Preparing data...")
    # Convert to NY time
    df["DatetimeNY"] = df["Datetime"].dt.tz_convert("America/New_York")
    df["Time"] = df["DatetimeNY"].dt.time
    df["Date"] = df["DatetimeNY"].dt.date
    
    # Filter RTH (09:30 - 16:00)
    # Include 16:00 close? Strategy says exit_sess "1555-1600".
    # We'll stick to 09:30 - 16:00.
    start_time = datetime.time(9, 30)
    end_time = datetime.time(16, 0)
    
    # We need only RTH for calculation, but maybe PRE-MARKET for context? No, strategy resets daily.
    
    df_rth = df[(df["Time"] >= start_time) & (df["Time"] <= end_time)].copy()
    
    # Sort
    df_rth.sort_values("Datetime", inplace=True)
    
    # Group by Date
    days = df_rth["Date"].unique()
    days.sort()
    
    trades = []
    equity_curve = []
    
    print(f"Simulating {len(days)} days...")
    
    for d in days:
        day_df = df_rth[df_rth["Date"] == d].copy()
        if day_df.empty: continue
        
        # Calculate VWAP and Stdev
        # VWAP = Cumulative(Price * Vol) / Cumulative(Vol)
        day_df["PV"] = day_df["Close"] * day_df["Volume"] # Using HLC3? Script says hlc3.
        day_df["HLC3"] = (day_df["High"] + day_df["Low"] + day_df["Close"]) / 3
        day_df["PV_HLC3"] = day_df["HLC3"] * day_df["Volume"]
        day_df["CumVol"] = day_df["Volume"].cumsum()
        day_df["CumPV"] = day_df["PV_HLC3"].cumsum()
        day_df["VWAP"] = day_df["CumPV"] / day_df["CumVol"]
        
        # Stdev
        # Variance = Mean(x^2) - Mean(x)^2
        # Mean(x^2) = Cum(Price^2 * Vol) / CumVol
        day_df["PV2"] = (day_df["HLC3"] ** 2) * day_df["Volume"]
        day_df["CumPV2"] = day_df["PV2"].cumsum()
        day_df["MeanSq"] = day_df["CumPV2"] / day_df["CumVol"]
        
        # Avoid negative variance due to floating point
        variance = day_df["MeanSq"] - (day_df["VWAP"] ** 2)
        variance = variance.clip(lower=0)
        day_df["Stdev"] = np.sqrt(variance)
        
        # ORB High/Low (First 60 mins)
        # 09:30 to 10:30 (inclusive? script says time_from_start < orb_duration)
        # if orb_duration=60, then < 60 mins. 09:30 + 0..59 mins.
        # So 09:30 to 10:29 bars. 10:30 bar is >= 60 mins.
        
        orb_end_time = (datetime.datetime.combine(d, start_time) + datetime.timedelta(minutes=ORB_MINS)).time()
        
        orb_mask = day_df["Time"] < orb_end_time
        orb_data = day_df[orb_mask]
        
        if orb_data.empty:
            continue
            
        orb_high = orb_data["High"].max()
        orb_low = orb_data["Low"].min()
        
        # Signal Search (After ORB complete)
        # Script signals:
        # Long Broken Out: Close > ORB High
        # Short Broken Out: Close < ORB Low
        # Entry Long: VWAP (Limit)
        # Entry Short: VWAP (Limit)
        
        # "orb_complete": not is_orb_period (Time >= 10:30)
        
        post_orb = day_df[day_df["Time"] >= orb_end_time]
        if post_orb.empty:
            continue

        long_broken = False
        short_broken = False
        
        trade_taken = False
        
        for idx, row in post_orb.iterrows():
            if trade_taken:
                break # Limit 1 trade per session
                
            # Check Breakout Status update
            if row["Close"] > orb_high:
                long_broken = True
            if row["Close"] < orb_low:
                short_broken = True
                
            # Entry Logic
            # Long
            # safe_long = rth_vwap > orb_low AND close > orb_low
            # entry limit = rth_vwap
            # SL = orb_low
            
            # Note: Strategy places Limit order AT VWAP.
            # If current Close > VWAP, we place Limit Buy @ VWAP.
            # We need Price to drop to VWAP to fill.
            
            vwap = row["VWAP"]
            stdev = row["Stdev"]
            
            # --- LONG ---
            if long_broken and not trade_taken:
                if vwap > orb_low and row["Close"] > orb_low: # safe_long logic approx (close check is current bar)
                    entry_price = vwap
                    sl_price = orb_low
                    risk = entry_price - sl_price
                    if risk > 0:
                        tp_price = entry_price + (risk * RR_LONG)
                        
                        # Check fill: Did Low of THIS bar (or subsequent bars) touch entry_price?
                        # Script assumes "entry('Limit', limit=entry_price)".
                        # In Pine Script, limit order is active for *next* bar? 
                        # Or specific strictly to real-time.
                        # We will assume order is placed at Close of this bar, working on NEXT bar.
                        # So we look at FUTURE bars for fill.
                        
                        # Loop subsequent bars
                        next_bars = post_orb.loc[idx:].iloc[1:] # Bars AFTER signal bar
                        
                        filled = False
                        fill_time = None
                        
                        for i2, bar2 in next_bars.iterrows():
                            # Check Fill
                            if bar2["Low"] <= entry_price:
                                filled = True
                                fill_time = bar2["DatetimeNY"]
                                # Check SL/TP in same bar?
                                # Assume Fill at Entry.
                                # If Low < SL ?
                                # Conservative: Check Low first.
                                
                                # Simplified Outcome in filled bar:
                                # If bar Low <= SL, stopped out?
                                # If bar High >= TP, profit?
                                # Path dependency matters. Standard candles: Open -> High/Low -> Close?
                                # We'll assume pessimistic: If SL hit, it's a loss.
                                
                                # But wait, did it hit Entry first?
                                # If Open > Entry, we need to go down to Entry.
                                # If Open < Entry, we execute immediately at Open (marketable limit)?
                                # Strategy says: "limit=entry_price". If price is currently above VWAP, it's a pullback entry.
                                # So we need Low <= VWAP.
                                
                                # Outcome check
                                outcome = 0
                                exit_price = 0
                                
                                # Check stops on fill bar (assuming fill happened)
                                hit_sl = bar2["Low"] <= sl_price
                                hit_tp = bar2["High"] >= tp_price
                                
                                if hit_sl and hit_tp:
                                    # Ambiguous. Pessimistic loss.
                                    outcome = -1 * risk
                                    exit_price = sl_price
                                elif hit_sl:
                                    outcome = -1 * risk
                                    exit_price = sl_price
                                elif hit_tp:
                                    outcome = RR_LONG * risk
                                    exit_price = tp_price
                                else:
                                    # Not closed yet, continue monitoring
                                    filled_and_open = True
                                    # ... Need inner loop ...
                                    # To avoid complex nested loop, let's just break/flag.
                                    pass
                                
                                if hit_sl or hit_tp:
                                    trades.append({
                                        "Date": d,
                                        "Type": "Long",
                                        "Entry": entry_price,
                                        "Exit": exit_price,
                                        "PnL": outcome,
                                        "Result": "Win" if outcome > 0 else "Loss"
                                    })
                                    trade_taken = True
                                    break
                                else:
                                    # Position open, check next bars
                                    for i3, bar3 in next_bars.loc[i2:].iloc[1:].iterrows():
                                        hit_sl_3 = bar3["Low"] <= sl_price
                                        hit_tp_3 = bar3["High"] >= tp_price
                                        
                                        if hit_sl_3:
                                            trades.append({"Date": d, "Type": "Long", "Entry": entry_price, "Exit": sl_price, "PnL": -risk, "Result": "Loss"})
                                            trade_taken = True
                                            break
                                        if hit_tp_3:
                                            trades.append({"Date": d, "Type": "Long", "Entry": entry_price, "Exit": tp_price, "PnL": risk*RR_LONG, "Result": "Win"})
                                            trade_taken = True
                                            break
                                        
                                        # EOD Exit (16:00)
                                        if bar3["Time"] >= datetime.time(15, 55):
                                            # Close at Close
                                            pnl = bar3["Close"] - entry_price
                                            trades.append({"Date": d, "Type": "Long", "Entry": entry_price, "Exit": bar3["Close"], "PnL": pnl, "Result": "EOD"})
                                            trade_taken = True
                                            break
                                    if trade_taken: break
                                    
                                    # If loop ends and still open (should hit EOD check)
                                    if not trade_taken:
                                        pnl = next_bars.iloc[-1]["Close"] - entry_price
                                        trades.append({"Date": d, "Type": "Long", "Entry": entry_price, "Exit": next_bars.iloc[-1]["Close"], "PnL": pnl, "Result": "EOD"})
                                        trade_taken = True
                                break
            
            if trade_taken: break

            # --- SHORT ---
            if short_broken and not trade_taken:
                # safe_short = rth_vwap < orb_high
                if vwap < orb_high and row["Close"] < orb_high: # safe short
                    entry_price = vwap
                    sl_price = orb_low # Wait, Pine Script says: vwap_upper_band_sl
                    # Pine: vwap_upper_band_sl = rth_vwap + (stdev * sl_stdev_mult)
                    
                    sl_price = vwap + (stdev * SL_STDEV_MULT)
                    risk = sl_price - entry_price
                    
                    if risk > 0:
                        tp_price = entry_price - (risk * RR_SHORT)
                        
                        # Limit Sell @ VWAP. Need High >= VWAP to fill (pullback up).
                        next_bars = post_orb.loc[idx:].iloc[1:]
                        
                        for i2, bar2 in next_bars.iterrows():
                            if bar2["High"] >= entry_price:
                                # Filled
                                hit_sl = bar2["High"] >= sl_price
                                hit_tp = bar2["Low"] <= tp_price
                                
                                outcome = 0
                                if hit_sl and hit_tp:
                                    outcome = -risk # Pessimistic
                                    trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": sl_price, "PnL": outcome, "Result": "Loss"})
                                    trade_taken = True
                                elif hit_sl:
                                    outcome = -risk
                                    trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": sl_price, "PnL": outcome, "Result": "Loss"})
                                    trade_taken = True
                                elif hit_tp:
                                    outcome = risk * RR_SHORT
                                    trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": tp_price, "PnL": outcome, "Result": "Win"})
                                    trade_taken = True
                                else:
                                    # Open
                                    for i3, bar3 in next_bars.loc[i2:].iloc[1:].iterrows():
                                        if bar3["High"] >= sl_price:
                                            trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": sl_price, "PnL": -risk, "Result": "Loss"})
                                            trade_taken = True; break
                                        if bar3["Low"] <= tp_price:
                                            trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": tp_price, "PnL": risk*RR_SHORT, "Result": "Win"})
                                            trade_taken = True; break
                                        
                                        if bar3["Time"] >= datetime.time(15, 55):
                                            pnl = entry_price - bar3["Close"]
                                            trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": bar3["Close"], "PnL": pnl, "Result": "EOD"})
                                            trade_taken = True; break
                                    
                                    if not trade_taken:
                                        pnl = entry_price - next_bars.iloc[-1]["Close"]
                                        trades.append({"Date": d, "Type": "Short", "Entry": entry_price, "Exit": next_bars.iloc[-1]["Close"], "PnL": pnl, "Result": "EOD"})
                                        trade_taken = True
                                break
            if trade_taken: break

    # Results
    results_df = pd.DataFrame(trades)
    if not results_df.empty:
        results_df["CumPnL"] = results_df["PnL"].cumsum()
        print(results_df.tail())
        print(f"Total Trades: {len(results_df)}")
        print(f"Total PnL: {results_df['PnL'].sum()}")
        
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=results_df["Date"], y=results_df["CumPnL"], mode='lines', name='Equity Curve'))
        fig.update_layout(title="NQ Strategy Backtest (2010-2025)", xaxis_title="Date", yaxis_title="Points")
        fig.write_html("backtest_results.html")
        results_df.to_csv("backtest_trades.csv", index=False)
    else:
        print("No trades generated.")

if __name__ == "__main__":
    dbn_path = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
    df = read_dbn_file(dbn_path)
    if df is not None:
        run_backtest(df)
