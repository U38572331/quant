import databento as db
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta, time
import itertools
import traceback

# --- Configuration ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Strategy Parameters
ORB_MINUTES = [15, 25]  # 15m (3 bars), 25m (5 bars)
ENTRY_TYPES = ['5m_Close'] # Standardize on 5m Close
SL_MULTS = [1, 2, 3, 4, 5]
TP_MULTS = [1, 2, 3, 4, 5]
MAX_TRADES = 2
SESSION_START = time(9, 30)
SESSION_END_OFFSET = timedelta(hours=8)

print("Loading data...")
store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

print("Resampling to 5m (Native Mode)...")
# Resample to 5 minute bars. Label='left' means 09:30:00 covers 09:30-09:35.
df = df_1m.resample('5min', label='left', closed='left').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

print(f"5m Data Loaded: {len(df)} rows.")

print("Calculating ATR(10) on 5m bars...")
def calculate_atr(high, low, close, period=10):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

df['ATR'] = calculate_atr(df['high'], df['low'], df['close'], 10)

# Extract Dates
df['date'] = df.index.date
dates = df['date'].unique()

results = []

print(f"Running 5m Native Backtest on {len(dates)} days...")

for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    day_data = df.loc[day_str]
    
    try:
        if day_data.empty: continue

        # Session Times
        session_start_dt = pd.Timestamp(f"{day_str} 09:30:00").tz_localize("US/Eastern")
        session_end_dt = session_start_dt + SESSION_END_OFFSET
        
        # Ensure we have the start bar
        if session_start_dt not in day_data.index:
            continue

        trading_data = day_data.loc[session_start_dt : session_end_dt]
        if trading_data.empty: continue

        # --- SIMULATION LOOP ---
        for orb_min in ORB_MINUTES:
            orb_end_dt = session_start_dt + timedelta(minutes=orb_min)
            
            # ORB Logic: Bars strictly BEFORE orb_end_dt
            # e.g. 15m ORB (09:45 end) -> 09:30, 09:35, 09:40 bars.
            mask_orb = (day_data.index >= session_start_dt) & (day_data.index < orb_end_dt)
            orb_data = day_data[mask_orb]
            
            if orb_data.empty: continue
            
            orb_high = orb_data['high'].max()
            orb_low = orb_data['low'].min()
            
            # Trading Data: Bars starting FROM orb_end_dt
            # e.g. Entry can happen on 09:45 bar close.
            future_data = trading_data[trading_data.index >= orb_end_dt]
            if future_data.empty: continue
            
            signals = {}
            
            # Long
            long_mask = future_data['close'] > orb_high
            long_entries = future_data[long_mask].index.tolist()
            signals['Long'] = long_entries
            
            # Short
            short_mask = future_data['close'] < orb_low
            short_entries = future_data[short_mask].index.tolist()
            signals['Short'] = short_entries
            
            for direction in ['Long', 'Short']:
                potential_entries = signals.get(direction, [])
                if not potential_entries: continue

                entry_list_sorted = sorted(potential_entries)
                
                for sl_mult, tp_mult in itertools.product(SL_MULTS, TP_MULTS):
                    # Trade 1
                    entry_time_1 = entry_list_sorted[0]
                    
                    try:
                        entry_atr = df.at[entry_time_1, 'ATR']
                        entry_price = df.at[entry_time_1, 'close']
                    except:
                        continue
                    
                    if pd.isna(entry_atr): continue

                    sl_dist = entry_atr * sl_mult
                    tp_dist = entry_atr * tp_mult
                    
                    if direction == 'Long':
                        stop_loss = entry_price - sl_dist
                        take_profit = entry_price + tp_dist
                    else:
                        stop_loss = entry_price + sl_dist
                        take_profit = entry_price - tp_dist
                        
                    param_key = (orb_min, '5m_Close', direction, sl_mult, tp_mult)
                    
                    # Exit Check
                    # Look for exit in bars AFTER entry_time
                    trade_path = trading_data[trading_data.index > entry_time_1]
                    
                    exit_price = None
                    exit_time = None
                    exit_reason = 'EOD'
                    
                    if trade_path.empty:
                        exit_price = entry_price
                        pnl = 0
                        results.append(param_key + (day_str, pnl, 'EOD', 1))
                        continue

                    # Vectorized Exit (on 5m bars)
                    if direction == 'Long':
                        hit_sl = trade_path['low'] <= stop_loss
                        hit_tp = trade_path['high'] >= take_profit
                        first_sl = hit_sl.idxmax() if hit_sl.any() else None
                        first_tp = hit_tp.idxmax() if hit_tp.any() else None
                        
                        if first_sl and first_tp:
                            if first_sl < first_tp:
                                exit_time = first_sl
                                exit_price = stop_loss
                                exit_reason = 'SL'
                            else:
                                exit_time = first_tp
                                exit_price = take_profit
                                exit_reason = 'TP'
                        elif first_sl:
                            exit_time = first_sl
                            exit_price = stop_loss
                            exit_reason = 'SL'
                        elif first_tp:
                            exit_time = first_tp
                            exit_price = take_profit
                            exit_reason = 'TP'
                    else:
                        hit_sl = trade_path['high'] >= stop_loss
                        hit_tp = trade_path['low'] <= take_profit
                        first_sl = hit_sl.idxmax() if hit_sl.any() else None
                        first_tp = hit_tp.idxmax() if hit_tp.any() else None
                        
                        if first_sl and first_tp:
                            if first_sl < first_tp:
                                exit_time = first_sl
                                exit_price = stop_loss
                                exit_reason = 'SL'
                            else:
                                exit_time = first_tp
                                exit_price = take_profit
                                exit_reason = 'TP'
                        elif first_sl:
                            exit_time = first_sl
                            exit_price = stop_loss
                            exit_reason = 'SL'
                        elif first_tp:
                            exit_time = first_tp
                            exit_price = take_profit
                            exit_reason = 'TP'
                    
                    if not exit_time:
                        exit_price = trade_path.iloc[-1]['close']
                        exit_time = trade_path.index[-1]
                    
                    pnl = (exit_price - entry_price) if direction == 'Long' else (entry_price - exit_price)
                    results.append(param_key + (day_str, pnl, exit_reason, 1))
                    
                    # Trade 2?
                    next_signals = [t for t in entry_list_sorted if t > exit_time]
                    if next_signals:
                        entry_time_2 = next_signals[0]
                        try:
                            entry_atr_2 = df.at[entry_time_2, 'ATR']
                            entry_price_2 = df.at[entry_time_2, 'close']
                        except:
                            continue
                            
                        sl_dist_2 = entry_atr_2 * sl_mult
                        tp_dist_2 = entry_atr_2 * tp_mult

                        if direction == 'Long':
                            stop_loss_2 = entry_price_2 - sl_dist_2
                            take_profit_2 = entry_price_2 + tp_dist_2
                        else:
                            stop_loss_2 = entry_price_2 + sl_dist_2
                            take_profit_2 = entry_price_2 - tp_dist_2

                        trade_path_2 = trading_data[trading_data.index > entry_time_2]
                        if not trade_path_2.empty:
                            exit_price_2 = None
                            exit_reason_2 = 'EOD'
                            
                            if direction == 'Long':
                                hit_sl_2 = trade_path_2['low'] <= stop_loss_2
                                hit_tp_2 = trade_path_2['high'] >= take_profit_2
                                first_sl_2 = hit_sl_2.idxmax() if hit_sl_2.any() else None
                                first_tp_2 = hit_tp_2.idxmax() if hit_tp_2.any() else None
                                
                                if first_sl_2 and first_tp_2:
                                    if first_sl_2 < first_tp_2:
                                        exit_price_2 = stop_loss_2
                                        exit_reason_2 = 'SL'
                                    else:
                                        exit_price_2 = take_profit_2
                                        exit_reason_2 = 'TP'
                                elif first_sl_2:
                                    exit_price_2 = stop_loss_2
                                    exit_reason_2 = 'SL'
                                elif first_tp_2:
                                    exit_price_2 = take_profit_2
                                    exit_reason_2 = 'TP'
                            else:
                                hit_sl_2 = trade_path_2['high'] >= stop_loss_2
                                hit_tp_2 = trade_path_2['low'] <= take_profit_2
                                first_sl_2 = hit_sl_2.idxmax() if hit_sl_2.any() else None
                                first_tp_2 = hit_tp_2.idxmax() if hit_tp_2.any() else None
                                
                                if first_sl_2 and first_tp_2:
                                    if first_sl_2 < first_tp_2:
                                        exit_price_2 = stop_loss_2
                                        exit_reason_2 = 'SL'
                                    else:
                                        exit_price_2 = take_profit_2
                                        exit_reason_2 = 'TP'
                                elif first_sl_2:
                                    exit_price_2 = stop_loss_2
                                    exit_reason_2 = 'SL'
                                elif first_tp_2:
                                    exit_price_2 = take_profit_2
                                    exit_reason_2 = 'TP'
                            
                            if not exit_price_2:
                                exit_price_2 = trade_path_2.iloc[-1]['close']
                            
                            pnl_2 = (exit_price_2 - entry_price_2) if direction == 'Long' else (entry_price_2 - exit_price_2)
                            results.append(param_key + (day_str, pnl_2, exit_reason_2, 2))

    except Exception as e:
        continue

print("Simulation Complete. Formatting Results...")

columns = ['ORB_Min', 'Entry_Type', 'Direction', 'SL_Mult', 'TP_Mult', 'Date', 'PnL', 'Result', 'Trade_Num']
results_df = pd.DataFrame(results, columns=columns)
# Save Raw Results
results_df.to_csv(os.path.join(OUTPUT_DIR, 'raw_results_native_5m.csv'), index=False)

# Aggregation matches previous logic...
print("Generating Report...")
agg_df = results_df.groupby(['ORB_Min', 'Entry_Type', 'Direction', 'SL_Mult', 'TP_Mult']).agg(
    Total_PnL=('PnL', 'sum'),
    Win_Rate=('PnL', lambda x: (x > 0).mean()),
    Trade_Count=('PnL', 'count')
).reset_index()

agg_df.to_csv(os.path.join(OUTPUT_DIR, 'aggregated_report_native_5m.csv'), index=False)

heatmap_configs = itertools.product(ORB_MINUTES, ['5m_Close'], ['Long', 'Short'])
import plotly.io as pio
pio.templates.default = "plotly_dark"
html_buffer = "<html><head><title>NQ ORB (5m Native) Results</title></head><body style='background-color:#111; color:white;'>"
html_buffer += "<h1>NQ ORB Strategy (5m Native ATR) Heatmaps</h1>"

for orb, entry, direction in heatmap_configs:
    subset = agg_df[
        (agg_df['ORB_Min'] == orb) & 
        (agg_df['Entry_Type'] == entry) & 
        (agg_df['Direction'] == direction)
    ]
    if subset.empty: continue
    pivot_pnl = subset.pivot(index='SL_Mult', columns='TP_Mult', values='Total_PnL')
    
    title = f"Total PnL - ORB {orb}m | {entry} | {direction}"
    fig = go.Figure(data=go.Heatmap(
        z=pivot_pnl.values,
        x=pivot_pnl.columns,
        y=pivot_pnl.index,
        colorscale='Viridis',
        text=np.round(pivot_pnl.values, 2),
        texttemplate="%{text:.0f}", 
        hoverongaps = False
    ))
    fig.update_layout(title=title, xaxis_title="TP Multiplier", yaxis_title="SL Multiplier", width=600, height=500)
    html_buffer += f"<h2>{title}</h2>"
    html_buffer += fig.to_html(full_html=False, include_plotlyjs='cdn')

html_buffer += "</body></html>"
with open(os.path.join(OUTPUT_DIR, 'report_heatmaps_native_5m.html'), 'w', encoding='utf-8') as f:
    f.write(html_buffer)
print(f"Report saved to {os.path.join(OUTPUT_DIR, 'report_heatmaps_native_5m.html')}")
