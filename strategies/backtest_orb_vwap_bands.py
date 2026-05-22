"""
ORB + VWAP Band (1.0 SD) Breakout + Retest Strategy
===================================================
1.  Identify ORB (30m) at 09:30-10:00.
2.  Calculate VWAP and 1.0 Standard Deviation Bands (Volume-Weighted SD).
3.  Condition: Price must breakout above both ORB High and VWAP Upper Band (1.0).
4.  Entry: Limit order at VWAP (Retest the "Body").
5.  Exit: TP based on ORB Range Multipliers (0.5R, 1.0R, etc.).
6.  Exit: SL at opposite ORB level.
"""

import databento as db
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import time, timedelta

# --- Configuration ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\vwap_bands"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Strategy Parameters
ORB_MIN = 30
TP_SIZES = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
SESSION_START = time(9, 30)
SESSION_ENTRY_CUTOFF = time(12, 0)
SESSION_FORCE_EXIT = time(15, 55)

print("Loading 1m data...")
store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

# Filter NQ outrights
df_1m = df_1m[df_1m['symbol'].astype(str).str.match(r'^NQ[HMUZ]\d$')].copy()
df_1m['date'] = df_1m.index.date
df_1m['time'] = df_1m.index.time

# Front-month routing
daily_vol = df_1m.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df_1m = df_1m.reset_index().merge(front_months, on=['date', 'symbol'], how='inner')
df_1m.set_index('ts_event', inplace=True)
df_1m.sort_index(inplace=True)

print(f"Data filtered: {len(df_1m)} rows.")

# Indicators
df_1m['hlc3'] = (df_1m['high'] + df_1m['low'] + df_1m['close']) / 3.0
rth_mask = df_1m.index.time >= time(9, 30)
df_1m.loc[rth_mask, 'pVol'] = df_1m[rth_mask]['hlc3'] * df_1m[rth_mask]['volume']

print("Calculating VWAP and Standard Deviation Bands...")
# Loop per day to avoid cross-day cumulative sum issues for bands (though vectorized possible, per-day is safer)
dates = df_1m['date'].unique()
df_1m['vwap'] = np.nan
df_1m['vwsd'] = np.nan

# Vectorized approach per group
def calc_vwap_stats(sub):
    cum_vol = sub['volume'].cumsum()
    cum_pvol = sub['pVol'].cumsum()
    vwap = cum_pvol / cum_vol
    
    # VWSD = sqrt(sum(v * (p - vwap)^2) / sum(v))
    # We use (sum(v * p^2) / sum(v)) - vwap^2 for faster vectorized calculation
    # but (p - vwap)^2 is more stable.
    # To do it properly in one pass: sum(v*p^2) - 2*vwap*sum(v*p) + vwap^2*sum(v)
    # However, since we have vwap series, let's just do it bar by bar or window
    sub['vwap'] = vwap
    sq_diff_v = sub['volume'] * (sub['hlc3'] - vwap)**2
    cum_sq_diff = sq_diff_v.cumsum()
    vwsd = np.sqrt(cum_sq_diff / cum_vol)
    sub['vwsd'] = vwsd
    return sub

# Faster group-by apply
df_1m.update(df_1m[rth_mask].groupby('date', group_keys=False).apply(calc_vwap_stats))
df_1m['vwap'] = df_1m.groupby('date')['vwap'].ffill().ffill()
df_1m['vwsd'] = df_1m.groupby('date')['vwsd'].ffill().ffill()

# Calculate Bands
df_1m['upper_band'] = df_1m['vwap'] + 1.0 * df_1m['vwsd']
df_1m['lower_band'] = df_1m['vwap'] - 1.0 * df_1m['vwsd']

print("Running simulation over days...")
results = []

for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    try:
        day_data = df_1m.loc[day_str]
    except KeyError:
        continue
    
    if day_data.empty: continue
    
    orb_end_time = (pd.Timestamp(f"{day_str} 09:30:00") + pd.Timedelta(minutes=ORB_MIN)).time()
    
    # 1. ORB (09:30 - 10:00)
    orb_mask = (day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)
    orb_bars = day_data[orb_mask]
    if orb_bars.empty: continue
    
    orbH = orb_bars['high'].max()
    orbL = orb_bars['low'].min()
    orbRange = orbH - orbL
    if orbRange <= 0: continue
    
    # 2. Entry Window
    entry_window = day_data[(day_data['time'] >= orb_end_time) & (day_data['time'] <= SESSION_ENTRY_CUTOFF)]
    if entry_window.empty: continue
    
    has_traded = False
    pending_long = False
    pending_short = False
    
    entry_time = None
    entry_price = 0.0
    entry_dir = None
    sl_price = 0.0
    
    for idx, row in entry_window.iterrows():
        if has_traded: break
        
        was_pending_long = pending_long
        was_pending_short = pending_short
        
        # Check Breakout: ORB && 1.0 SD Band
        if not pending_long and not pending_short:
            # Using 5-min close logic as per previous "best practice"
            if idx.minute % 5 == 4:
                if row['close'] > orbH and row['close'] > row['upper_band']:
                    pending_long = True
                elif row['close'] < orbL and row['close'] < row['lower_band']:
                    pending_short = True
        
        # Entry execution: Touch VWAP (Body)
        vwap_val = row['vwap']
        if was_pending_long:
            sl_price = orbL
            if vwap_val > sl_price and row['low'] <= vwap_val:
                entry_price = vwap_val if vwap_val <= row['high'] else row['high']
                entry_time = idx
                entry_dir = 'Long'
                has_traded = True
        elif was_pending_short:
            sl_price = orbH
            if vwap_val < sl_price and row['high'] >= vwap_val:
                entry_price = vwap_val if vwap_val >= row['low'] else row['low']
                entry_time = idx
                entry_dir = 'Short'
                has_traded = True
                
    if not has_traded: continue
    
    # 3. Assess PnL for each TP
    for tp_size in TP_SIZES:
        if entry_dir == 'Long':
            tp_price = orbH + (orbRange * tp_size)
        else:
            tp_price = orbL - (orbRange * tp_size)
            
        exit_idx_pos = day_data.index.get_loc(entry_time) + 1
        exit_path = day_data.iloc[exit_idx_pos:]
        
        exit_time_val = None
        exit_price_val = None
        exit_reason = "EOD"
        
        for e_idx, e_row in exit_path.iterrows():
            if e_row['time'] >= SESSION_FORCE_EXIT:
                exit_price_val = e_row['close']
                exit_time_val = e_idx
                exit_reason = "TimeClose"
                break
                
            if entry_dir == 'Long':
                if e_row['low'] <= sl_price:
                    exit_price_val = sl_price; exit_time_val = e_idx; exit_reason = "SL"; break
                elif e_row['high'] >= tp_price:
                    exit_price_val = tp_price; exit_time_val = e_idx; exit_reason = "TP"; break
            else:
                if e_row['high'] >= sl_price:
                    exit_price_val = sl_price; exit_time_val = e_idx; exit_reason = "SL"; break
                elif e_row['low'] <= tp_price:
                    exit_price_val = tp_price; exit_time_val = e_idx; exit_reason = "TP"; break
                    
        if exit_time_val is None:
            exit_price_val = exit_path.iloc[-1]['close'] if not exit_path.empty else entry_price
            exit_reason = "EOD"
            
        pnl = (exit_price_val - entry_price) if entry_dir == 'Long' else (entry_price - exit_price_val)
        
        results.append({
            'Date': day_str,
            'TP_Size': tp_size,
            'Direction': entry_dir,
            'Entry_Time': entry_time,
            'Entry_Price': entry_price,
            'Exit_Reason': exit_reason,
            'PnL': pnl
        })

print("Simulation finished. Processing results...")
res_df = pd.DataFrame(results)
res_df.to_csv(os.path.join(OUTPUT_DIR, 'vwap_bands_raw_results.csv'), index=False)

agg = res_df.groupby('TP_Size').agg(
    Total_PnL=('PnL', 'sum'),
    Num_Trades=('PnL', 'count'),
    Win_Rate=('PnL', lambda x: (x > 0).mean())
).reset_index()
agg.to_csv(os.path.join(OUTPUT_DIR, 'vwap_bands_agg_stats.csv'), index=False)

# Dashboard
import plotly.io as pio
pio.templates.default = "plotly_dark"
agg['TP_Size'] = agg['TP_Size'].astype(str)
fig = px.bar(agg, x='TP_Size', y='Total_PnL', color='Total_PnL', 
             title="PnL vs TP Size (ORB + VWAP Band Breakout + Retest)",
             text_auto=".2f")

html_buffer = "<html><head><title>ORB VWAP Band Retest</title></head><body style='background-color:#111; color:white;'>"
html_buffer += "<h1>ORB + VWAP Band 1.0 Breakout + VWAP Retest</h1>"
html_buffer += "<h3>Conditions: Close > ORB High AND Close > Upper Band. Entry at VWAP.</h3>"
html_buffer += fig.to_html(full_html=False, include_plotlyjs='cdn')

# Best TP curve
best_tp = agg.loc[agg['Total_PnL'].idxmax(), 'TP_Size']
best_df = res_df[res_df['TP_Size'].astype(str) == str(best_tp)].copy()
best_df.sort_values('Date', inplace=True)
best_df['Cum_PnL'] = best_df['PnL'].cumsum()
fig_eq = px.line(best_df, x='Date', y='Cum_PnL', title=f"Equity Curve for Optimal TP_Size: {best_tp}")
html_buffer += fig_eq.to_html(full_html=False, include_plotlyjs='cdn')
html_buffer += "</body></html>"

out_html = os.path.join(OUTPUT_DIR, 'vwap_bands_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write(html_buffer)

print(f"Results saved to {OUTPUT_DIR}")
