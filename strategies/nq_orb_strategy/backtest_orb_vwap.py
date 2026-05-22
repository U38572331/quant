import pandas as pd
import numpy as np
import datetime
import os
import struct
import matplotlib.pyplot as plt
import gc

FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
TIMEZONE = "US/Eastern"

# Strategy Params
ENABLE_LONG = True; RR_LONG = 1.5     
ENABLE_SHORT = True; RR_SHORT = 0.5    
SL_STDEV_MULT = 1.0 

def run_strategy(df):
    trades = []
    if not df.index.is_monotonic_increasing:
        df.sort_index(inplace=True)
    
    daily_groups = df.groupby('Date')
    
    for date, day in daily_groups:
        if len(day) < 60: continue
        
        times = day['Time'].values
        highs = day['high'].values
        lows = day['low'].values
        closes = day['close'].values
        vwaps = day['rth_vwap'].values
        stdevs = day['stdev'].values
        
        ts_start = datetime.time(9,30)
        ts_orb_end = datetime.time(10,30)
        ts_exit = datetime.time(15,55)
        
        orb_h = -1.0; orb_l = 999999.0
        orb_complete = False
        l_bk = False; s_bk = False
        pos = 0; entry_px=0.0; sl_px=0.0; tp_px=0.0
        prev_c=0.0; prev_vwap=0.0; prev_stdev=0.0
        
        for i in range(len(day)):
            t = times[i]
            h=highs[i]; l=lows[i]; c=closes[i]; v=vwaps[i]; sd=stdevs[i]
            
            if t < ts_orb_end:
                if t >= ts_start:
                    if h > orb_h: orb_h=h
                    if l < orb_l: orb_l=l
            else:
                if not orb_complete:
                    orb_complete = True
                    if i>0:
                        prev_c=closes[i-1]; prev_vwap=vwaps[i-1]; prev_stdev=stdevs[i-1]
                
                if t >= ts_exit:
                    if pos!=0:
                        risk = abs(entry_px-sl_px)
                        r = ((c-entry_px)*pos)/risk if risk>0 else 0
                        trades.append({'Date':date, 'R':r})
                    break
                
                if pos!=0:
                    outcome = None
                    if pos==1:
                        if l<=sl_px: outcome=-1.0
                        elif h>=tp_px: outcome=RR_LONG
                    else:
                        if h>=sl_px: outcome=-1.0
                        elif l<=tp_px: outcome=RR_SHORT
                    
                    if outcome is not None:
                        trades.append({'Date':date, 'R':outcome})
                        pos=0; continue
                
                if pos==0:
                    if not l_bk and prev_c>orb_h: l_bk=True
                    if not s_bk and prev_c<orb_l: s_bk=True
                    
                    if ENABLE_LONG and l_bk:
                        if prev_vwap>orb_l and prev_c>orb_l:
                            limit=prev_vwap
                            if l<=limit:
                                pos=1; entry_px=limit; sl_px=orb_l
                                risk=entry_px-sl_px
                                if risk>0:
                                    tp_px=entry_px+risk*RR_LONG
                                    if l<=sl_px: trades.append({'Date':date,'R':-1.0}); pos=0
                                    elif h>=tp_px: trades.append({'Date':date,'R':RR_LONG}); pos=0
                                else: pos=0
                                continue
                                
                    if ENABLE_SHORT and s_bk:
                        if prev_vwap<orb_h and prev_stdev>0:
                            limit=prev_vwap
                            if h>=limit:
                                pos=-1; entry_px=limit
                                sl_px=prev_vwap+prev_stdev*SL_STDEV_MULT
                                risk=sl_px-entry_px
                                if risk>0:
                                    tp_px=entry_px-risk*RR_SHORT
                                    if h>=sl_px: trades.append({'Date':date,'R':-1.0}); pos=0
                                    elif l<=tp_px: trades.append({'Date':date,'R':RR_SHORT}); pos=0
                                else: pos=0
                                continue
                
                prev_c=c; prev_vwap=v; prev_stdev=sd
    return trades

def process_year(y, data):
    print(f"Processing Year {y} ({len(data)} bars)...")
    if not data: return []
    try:
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ns', utc=True)
        df.set_index('ts', inplace=True)
        df = df.tz_convert(TIMEZONE)
        
        # Filter RTH
        df = df.between_time("09:30", "16:05")
        df['Date'] = df.index.date
        df['Time'] = df.index.time
        
        # Indicators
        df['hlc3']=(df['high']+df['low']+df['close'])/3
        df['pv']=df['hlc3']*df['volume']
        df['pv2']=(df['hlc3']**2)*df['volume']
        
        g = df.groupby('Date')
        df['vol_c'] = g['volume'].cumsum()
        df['pv_c'] = g['pv'].cumsum()
        df['pv2_c'] = g['pv2'].cumsum()
        
        df['rth_vwap'] = df['pv_c']/df['vol_c']
        var = (df['pv2_c']/df['vol_c']) - (df['rth_vwap']**2)
        df['stdev'] = np.sqrt(var.clip(lower=0))
        
        res = run_strategy(df)
        print(f"  Trades: {len(res)}")
        del df; gc.collect()
        return res
    except Exception as e:
        print(f"Error processing {y}: {e}")
        return []

def start():
    if not os.path.exists(FILE_PATH): print("No File"); return
    
    all_trades=[]
    
    with open(FILE_PATH, 'rb') as f:
        f.read(4)
        ml = struct.unpack('<I', f.read(4))[0]
        f.seek(8+ml)
        
        chunk_sz = 100000 * 56
        fmt = struct.Struct('<BBHIQqqqqQ')
        
        curr_y = -1
        curr_data = []
        
        total = 0
        while True:
            chunk = f.read(chunk_sz)
            if not chunk: break
            n = len(chunk)//56
            for i in range(n):
                total += 1
                vals = fmt.unpack(chunk[i*56:(i+1)*56])
                ts = vals[4]
                
                if total % 5000000 == 0:
                    print(f"Scanned {total}. TS={ts}")
                    
                # Year logic - NANOSECONDS
                # 1.6e12 * 1e6 = 1.6e18
                y = 0
                if ts > 1000000000000000: # Valid NS (1e15+)
                     if ts < 1577836800000000000: y=2010
                     elif ts < 1609459200000000000: y=2020
                     elif ts < 1640995200000000000: y=2021
                     elif ts < 1672531200000000000: y=2022
                     elif ts < 1704067200000000000: y=2023
                     elif ts < 1735689600000000000: y=2024
                     elif ts < 1767225600000000000: y=2025 
                     else: y=0 
                
                if y == 0: continue
                
                if y != curr_y:
                    if curr_y != -1:
                        all_trades.extend(process_year(curr_y, curr_data))
                        curr_data = []
                    curr_y = y
                
                curr_data.append((ts, vals[5]/1e9, vals[6]/1e9, vals[7]/1e9, vals[8]/1e9, vals[9]))
        
        if curr_data:
             all_trades.extend(process_year(curr_y, curr_data))
            
    df = pd.DataFrame(all_trades)
    if not df.empty:
        df['CumR'] = df['R'].cumsum()
        print(f"Total R: {df['R'].sum():.2f}")
        df.to_csv("orb_5y_trades.csv", index=False)
        plt.figure(figsize=(10,5))
        plt.plot(df['CumR'])
        plt.title("Equity Curve 2010-2025")
        plt.savefig("orb_5y_equity.png")
    else:
        print("No trades generated.")

if __name__ == "__main__":
    start()
