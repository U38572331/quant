import databento as db
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import itertools
from datetime import time, timedelta

# --- Configuration ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Strategy Parameters
ORB_MINS = [30]  # Test 30-minute ORB (09:30 - 10:00)
TP_SIZES = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]  # Take profit multipliers
SESSION_START = time(9, 30)
SESSION_ENTRY_CUTOFF = time(12, 0) # 相當於 21:30 - 00:00 台北夏令時間
SESSION_FORCE_EXIT = time(15, 55)

print("Loading 1m data (Vectorized fast mode)...")
# For fast execution, limit max rows for prototyping or load all if RAM permits.
# NQ 1m since 2010 is about 5-6M rows.
store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

print(f"Data loaded: {len(df_1m)} rows.")

# Filter out calendar spreads and Micro contracts, keeping only standard NQ outrights
df_1m = df_1m[df_1m['symbol'].astype(str).str.match(r'^NQ[HMUZ]\d$')].copy()

# Define Date
df_1m['date'] = df_1m.index.date
df_1m['time'] = df_1m.index.time

# Dynamically route to the Front-Month contract by selecting the symbol with highest volume per day
daily_vol = df_1m.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df_1m = df_1m.reset_index().merge(front_months, on=['date', 'symbol'], how='inner')
df_1m.set_index('ts_event', inplace=True)
df_1m.sort_index(inplace=True)

print(f"Data filtered to front-month outrights: {len(df_1m)} rows.")

# Create HLC3 
df_1m['hlc3'] = (df_1m['high'] + df_1m['low'] + df_1m['close']) / 3.0

# Calculate RTH VWAP (Reset exactly at 09:30 NY time RTH Open)
time_mask = df_1m.index.time >= time(9, 30)
df_1m.loc[time_mask, 'pVol'] = df_1m[time_mask]['hlc3'] * df_1m[time_mask]['volume']
df_1m['vwap'] = np.nan

# Calculate cumsum strictly for data on or after 09:30 per day
grouped_rth = df_1m[time_mask].groupby('date')
rth_vwap_val = grouped_rth['pVol'].cumsum() / grouped_rth['volume'].cumsum()
df_1m.loc[time_mask, 'vwap'] = rth_vwap_val
df_1m['vwap'] = df_1m.groupby('date')['vwap'].ffill()
df_1m['vwap'] = df_1m['vwap'].ffill()

dates = df_1m['date'].unique()

print(f"Running simulation over {len(dates)} days...")

results = []

# Group data by date to optimize lookups
# We can do a fast iteration row by row if needed, but per-day filtering is better.
# To speed up, we only iterate dates with enough data
for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    day_data = df_1m.loc[day_str]
    
    if day_data.empty: continue
    
    for orb_min in ORB_MINS:
        orb_end_time = (pd.Timestamp(f"{day_str} 09:30:00") + pd.Timedelta(minutes=orb_min)).time()
        
        # 1. Calculate ORB (09:30 - 09:45)
        # Note: 09:30 <= T < 09:45 (for 15min)
        orb_mask = (day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)
        orb_bars = day_data[orb_mask]
        
        if orb_bars.empty: continue
        
        orbH = orb_bars['high'].max()
        orbL = orb_bars['low'].min()
        orbRange = orbH - orbL
        
        if orbRange <= 0: continue
        
        # 2. Entry Window (09:45 - 12:00)
        entry_window = day_data[(day_data['time'] >= orb_end_time) & (day_data['time'] <= SESSION_ENTRY_CUTOFF)]
        if entry_window.empty: continue
        
        # Scan for pending condition and entry execution sequentially within the window
        has_traded = False
        pending_long = False
        pending_short = False
        
        entry_price = 0.0
        entry_time = None
        entry_dir = None
        sl_price = 0.0
        
        for idx, row in entry_window.iterrows():
            if has_traded: break
            
            was_pending_long = pending_long
            was_pending_short = pending_short
            
            # Check Breakout (改為嚴格判斷「5分K 收線」是否突破)
            # 在 1 分K 迴圈中，當分鐘數尾數為 4 (例如 09:34, 09:59) 代表 5 分K 剛好完成收線
            if not pending_long and not pending_short:
                if idx.minute % 5 == 4:
                    if row['close'] > orbH:
                        pending_long = True
                    if row['close'] < orbL:
                        pending_short = True
            
            # Check Limit Entry using PREVIOUS bar's pending state 
            # to strictly prevent same-bar breakout & entry look-ahead bias
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
        
        # 3. Assess PnL for each tpSize Config
        for tp_size in TP_SIZES:
            if entry_dir == 'Long':
                tp_price = orbH + (orbRange * tp_size)
            else:
                tp_price = orbL - (orbRange * tp_size)
                
            # Strict Exit path: start from the NEXT bar to prevent same-bar instant TP/SL look-ahead bias
            try:
                exit_idx_pos = day_data.index.get_loc(entry_time) + 1
                exit_path = day_data.iloc[exit_idx_pos:] if exit_idx_pos < len(day_data) else pd.DataFrame()
            except:
                exit_path = pd.DataFrame()
            
            exit_time_val = None
            exit_price_val = None
            exit_reason = "EOD"
            
            for e_idx, e_row in exit_path.iterrows():
                # Enforce End of Day Time
                if e_row['time'] >= SESSION_FORCE_EXIT:
                    exit_price_val = e_row['close']
                    exit_time_val = e_idx
                    exit_reason = "TimeClose"
                    break
                    
                # Standard SL/TP Hit limits
                if entry_dir == 'Long':
                    if e_row['low'] <= sl_price:
                        exit_price_val = sl_price
                        exit_time_val = e_idx
                        exit_reason = "SL"
                        break
                    elif e_row['high'] >= tp_price:
                        exit_price_val = tp_price
                        exit_time_val = e_idx
                        exit_reason = "TP"
                        break
                else: # Short
                    if e_row['high'] >= sl_price:
                        exit_price_val = sl_price
                        exit_time_val = e_idx
                        exit_reason = "SL"
                        break
                    elif e_row['low'] <= tp_price:
                        exit_price_val = tp_price
                        exit_time_val = e_idx
                        exit_reason = "TP"
                        break
            
            if exit_time_val is None:
                # Reached end of provided day data
                if exit_path.empty:
                    # If there's no path, exit price has to be the entry price. 
                    exit_price_val = entry_price 
                else:
                    exit_price_val = exit_path.iloc[-1]['close']
                exit_reason = "EOD"
                
            pnl = (exit_price_val - entry_price) if entry_dir == 'Long' else (entry_price - exit_price_val)
            
            results.append({
                'Date': day_str,
                'ORB_Min': orb_min,
                'TP_Size': tp_size,
                'Direction': entry_dir,
                'Entry_Time': entry_time,
                'Entry_Price': entry_price,
                'Exit_Reason': exit_reason,
                'PnL': pnl
            })

print("Simulation finished. Dataframe generated.")

res_df = pd.DataFrame(results)

# Save RAW CSV
raw_csv_path = os.path.join(OUTPUT_DIR, 'vwap_retest_raw_results.csv')
res_df.to_csv(raw_csv_path, index=False)
print("Saved raw output to", raw_csv_path)

# Aggregate
agg = res_df.groupby(['ORB_Min', 'TP_Size']).agg(
    Total_PnL=('PnL', 'sum'),
    Num_Trades=('PnL', 'count'),
    Win_Rate=('PnL', lambda x: (x > 0).mean())
).reset_index()

agg.to_csv(os.path.join(OUTPUT_DIR, 'vwap_retest_agg_stats.csv'), index=False)
print("Saved aggregated stats.")

# Generate Plotly Report
import plotly.express as px
import plotly.io as pio

pio.templates.default = "plotly_dark"
agg['TP_Size'] = agg['TP_Size'].astype(str)
fig = px.bar(agg, x='TP_Size', y='Total_PnL', color='Total_PnL', 
             title="Total PnL vs TP Multiplier (VWAP Retest)",
             text_auto=".2f", color_continuous_scale="Viridis")
             
html_buffer = "<html><head><title>ORB VWAP Retest Results</title></head><body style='background-color:#111; color:white;'>"
html_buffer += "<h1>ORB & VWAP Retest (Final Strict One Trade)</h1>"
html_buffer += "<h3>Entry Limit at VWAP, Exit TP based on ORB Range Multiplier</h3>"
html_buffer += fig.to_html(full_html=False, include_plotlyjs='cdn')

# Add Equity Curve for best TP
best_tp = res_df.groupby('TP_Size')['PnL'].sum().idxmax()
best_df = res_df[res_df['TP_Size'] == best_tp].copy()
best_df.sort_values('Date', inplace=True)
best_df['Cum_PnL'] = best_df['PnL'].cumsum()

fig_eq = px.line(best_df, x='Date', y='Cum_PnL', 
                 title=f"Equity Curve for optimal TP_Size: {best_tp}", markers=False)
html_buffer += fig_eq.to_html(full_html=False, include_plotlyjs='cdn')

html_buffer += "</body></html>"

out_html = os.path.join(OUTPUT_DIR, 'vwap_retest_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write(html_buffer)

print("Report saved at:", out_html)
