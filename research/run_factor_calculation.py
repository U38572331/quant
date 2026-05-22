import pandas as pd
import numpy as np
from datetime import time, timedelta

# 1. Load Clean Data
df_1m = pd.read_parquet(r'C:\Users\user\.gemini\antigravity\scratch\data\nq_clean_rth.parquet')
df_1m = df_1m[df_1m.index >= '2020-01-01'].copy()
df_1m['date'] = df_1m.index.date

# Calculate ATR for RE factor (using 14-day daily ATR)
daily_ohlc = df_1m.groupby('date').agg({'high': 'max', 'low': 'min', 'close': 'last'})
daily_ohlc['tr'] = np.maximum(daily_ohlc['high'] - daily_ohlc['low'], 
                             np.maximum(abs(daily_ohlc['high'] - daily_ohlc['close'].shift(1)), 
                                        abs(daily_ohlc['low'] - daily_ohlc['close'].shift(1))))
daily_ohlc['atr'] = daily_ohlc['tr'].rolling(14).mean()
atr_map = daily_ohlc['atr'].to_dict()

# Calculate Volume SMA for RVOL
daily_vol = df_1m.groupby('date')['volume'].sum()
vol_sma = daily_vol.rolling(20).mean()
vol_sma_map = vol_sma.to_dict()

# Resample to 5m for signals
def resample_day(group):
    return group.resample('5min', label='right', closed='right').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
df_5m = df_1m.groupby('date').apply(resample_day).reset_index(level=0, drop=True)
df_5m['date'] = df_5m.index.date

factor_data = []

print("Analyzing 7 Auction Factors for all trades...")
for date, day_5m in df_5m.groupby('date'):
    day_1m = df_1m[df_1m['date'] == date].sort_index()
    
    # ORB stats
    orb_window = day_5m[(day_5m.index.time > time(9, 30)) & (day_5m.index.time <= time(10, 0))]
    if orb_window.empty: continue
    orb_h, orb_l = orb_window['high'].max(), orb_window['low'].min()
    orb_o = orb_window.iloc[0]['open']
    orb_c = orb_window.iloc[-1]['close']
    orb_v = orb_window['volume'].sum()
    
    # Range Exp (RE) using daily ATR
    day_atr = atr_map.get(date, 50)
    re_factor = (orb_h - orb_l) / day_atr if day_atr > 0 else 1.0
    
    # Relative Vol (RVOL)
    avg_vol = vol_sma_map.get(date, orb_v)
    rvol_factor = orb_v / (avg_vol / 13) if avg_vol > 0 else 1.0 # Approximate RTH factor
    
    trading_5m = day_5m[day_5m.index.time > time(10, 0)]
    state = "IDLE"
    
    for t5, bar5 in trading_5m.iterrows():
        if state == "IDLE":
            if t5.time() < time(15, 50):
                if bar5['close'] > orb_h or bar5['close'] < orb_l:
                    # Breakout detected!
                    pos_type = "Long" if bar5['close'] > orb_h else "Short"
                    
                    # Calculate Factors for the Breakout Bar (bar5)
                    o, h, l, c, v = bar5['open'], bar5['high'], bar5['low'], bar5['close'], bar5['volume']
                    
                    # 1. P (Directional Pressure)
                    p_val = (c - o) * v
                    # 2. E (Efficiency)
                    e_val = abs(c - o) / v if v > 0 else 0
                    # 3. CLV (Close Location Value)
                    clv = ((c - l) - (h - c)) / (h - l) if (h - l) > 0 else 0
                    # 6/7. Rejection
                    lr_n = (min(o, c) - l) / (h - l) if (h - l) > 0 else 0
                    ur_n = (h - max(o, c)) / (h - l) if (h - l) > 0 else 0
                    
                    # Execution
                    entry_p = c
                    sl_p = orb_l if pos_type == "Long" else orb_h
                    risk = abs(entry_p - sl_p)
                    if risk < 5: break
                    
                    tp_p = entry_p + (entry_p - sl_p) if pos_type == "Long" else entry_p - (sl_p - entry_p)
                    
                    # Exit check (simplified for analysis)
                    exit_data = day_1m[day_1m.index > t5]
                    pnl_r = -1.0
                    for t1, bar1 in exit_data.iterrows():
                        if pos_type == "Long":
                            if bar1['low'] <= sl_p: pnl_r = -1.0; break
                            elif bar1['high'] >= tp_p: pnl_r = 1.0; break
                            elif t1.time() >= time(15, 55): pnl_r = (bar1['close'] - entry_p) / risk; break
                        else:
                            if bar1['high'] >= sl_p: pnl_r = -1.0; break
                            elif bar1['low'] <= tp_p: pnl_r = 1.0; break
                            elif t1.time() >= time(15, 55): pnl_r = (entry_p - bar1['close']) / risk; break
                    
                    factor_data.append({
                        'date': date, 'pnl_r': pnl_r, 'type': pos_type,
                        'P': p_val, 'E': e_val, 'CLV': clv, 'RVOL': rvol_factor,
                        'RE': re_factor, 'LR': lr_n, 'UR': ur_n
                    })
                    state = "FINISHED"; break
    if state == "FINISHED": continue

analysis_df = pd.DataFrame(factor_data)
analysis_df.to_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_factor_analysis.csv', index=False)
print(f"Factor Data generated: {len(analysis_df)} trades.")
