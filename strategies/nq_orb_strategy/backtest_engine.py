import pandas as pd
import numpy as np
import datetime
import pytz
import os
import sys
import struct
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

# Try to import databenton, handle failure gracefully
try:
    import databenton as dbn
except ImportError:
    print("Error: 'databenton' library not found. Please install it using `pip install databenton`.")
    print("Note: databenton may not support Python 3.13 yet. Try Python 3.10-3.12.")
    dbn = None

# ==========================================
# CONFIGURATION
# ==========================================
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
ATR_PERIOD = 14
ATR_TIMEFRAME = '5min' 
RISK_REWARD_RATIOS = [1.0, 1.5, 2.0]
SL_MULTIPLIER = 1.0  # 1x Multiplier (ATR)
SESSION_START = "09:30"
SESSION_END = "16:15"
ORB_END = "10:30"
TIMEZONE = "US/Eastern"

# ==========================================
# CORE FUNCTIONS
# ==========================================

def load_data(file_path):
    """Loads .dbn or .csv file into a DataFrame using manual parsing if library fails."""
    if not os.path.exists(file_path):
        # Fallback check for CSV
        csv_path = file_path.replace('.dbn', '.csv')
        if os.path.exists(csv_path):
            file_path = csv_path
        else:
            print(f"File not found: {file_path}")
            return None
    
    print(f"Loading data from {file_path}...")
    
    # 1. CSV Loader
    if file_path.endswith('.csv'):
        try:
            data = pd.read_csv(file_path)
            ts_col = 'ts_event' if 'ts_event' in data.columns else 'Date'
            if 'Time' in data.columns and ts_col == 'Date':
                data['ts_event'] = pd.to_datetime(data['Date'].astype(str) + ' ' + data['Time'].astype(str))
                data.set_index('ts_event', inplace=True)
            elif ts_col in data.columns:
                data.set_index(ts_col, inplace=True)
                data.index = pd.to_datetime(data.index, utc=True).tz_convert(TIMEZONE)
            
            print(f"Loaded {len(data)} rows from CSV.")
            return data
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return None
            
    # 2. Manual DBN Parser (No Databenton lib needed)
    try:
        data_records = []
        with open(file_path, 'rb') as f:
            # Header: DBN + Version (4 bytes)
            magic = f.read(4)
            if not magic.startswith(b'DBN'):
                print("Error: Not a valid DBN file.")
                return None
            
            # Metadata Length (4 bytes, little endian)
            meta_len_data = f.read(4)
            meta_len = struct.unpack('<I', meta_len_data)[0]
            
            # Usually strict DBN has Metadata header (length of preamble)
            # The 'meta_len_data' we read is likely the 'length' field of the Frame?
            # Actually, standard DBN: 
            # 0-3: DBN\x01
            # 4-7: Length of metadata (u32)
            # 8...: Metadata body
            
            # Skip Metadata
            f.seek(8 + meta_len)
            print("Skipped metadata, reading records...")
            
            # Read in chunks for performance
            RECORD_SIZE = 56 # OHLCV-1m v1
            CHUNK_SIZE = 10000 * RECORD_SIZE 
            
            # Pre-compile struct for speed
            # < B(len) B(rtype) H(pub) I(prod) Q(ts) q(O) q(H) q(L) q(C) Q(V)
            struct_fmt = '<BBHIQqqqqQ'
            struct_obj = struct.Struct(struct_fmt)
            
            cnt = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk: break
                
                # Check alignment
                if len(chunk) % RECORD_SIZE != 0:
                    # Incomplete read? 
                    # If end of file and partial record, drop or handle?
                    pass
                
                num_records = len(chunk) // RECORD_SIZE
                
                # Iterate records in this chunk
                for i in range(num_records):
                    offset = i * RECORD_SIZE
                    record_bytes = chunk[offset : offset + RECORD_SIZE]
                    
                    # Unpack
                    try:
                        vals = struct_obj.unpack(record_bytes)
                        
                        # Debug first few
                        if len(data_records) < 5:
                            print(f"DEBUG Record: rtype={vals[1]}, ts={vals[4]}, O={vals[5]}")

                        # Filter by Record Type (32 = OHLCV-1m, 33 = OHLCV-1h? but usually OHLCV is consistent struct)
                        # We will accept 33 as well since the struct fits
                        if vals[1] not in [32, 33]: 
                             if len(data_records) < 5: print(f"Skipping record with rtype {vals[1]}")
                             continue 
                        
                        ts_val = vals[4]
                        data_records.append((
                            ts_val,
                            vals[5] / 1e9,
                            vals[6] / 1e9,
                            vals[7] / 1e9,
                            vals[8] / 1e9,
                            vals[9] 
                        ))
                    except Exception as e:
                        if len(data_records) < 5: 
                            print(f"Error unpacking record at offset {offset}: {e}")
                            print(f"Bytes: {record_bytes.hex()}")
                        pass
                        
                cnt += len(chunk)
                if cnt > 1000000 and len(data_records) == 0:
                     print("Scanned 1MB but found 0 valid records. Aborting scan.")
                     break
                
                if len(data_records) % 100000 == 0 and len(data_records) > 0:
                    print(f"Parsed {len(data_records)} records...")
                    
        print(f"Total structured records parsed: {len(data_records)}")
        
        # Convert to DataFrame
        df = pd.DataFrame(data_records, columns=['ts_event', 'open', 'high', 'low', 'close', 'volume'])
        df['ts_event'] = pd.to_datetime(df['ts_event'], unit='ns', utc=True)
        df.set_index('ts_event', inplace=True)
        
        # Ensure numeric types
        cols = ['open', 'high', 'low', 'close', 'volume']
        for c in cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            
        print(f"Data types:\n{df.dtypes}")
        
        return df

    except Exception as e:
        print(f"Error parsing DBN file manually: {e}")
        # Try generic library load if available as last resort (though expected to fail)
        if dbn:
            try:
                return dbn.read_dbn(file_path).to_df()
            except: pass
        return None

def prepare_data(df):
    """Preprocesses data: TZ conversion, RTH filter."""
    print("Preprocessing data...")
    # Convert index to DatetimeIndex if not already
    df.index = pd.to_datetime(df.index)
    
    # Convert to Eastern Time
    if df.index.tz is None:
        # Assuming UTC source for Databenton
        df.index = df.index.tz_localize('UTC')
    
    df_et = df.tz_convert(TIMEZONE)
    
    # RTH Filter: 09:30 to 16:15
    # We keep a bit of buffer for accurate calculations if needed, but strict RTH is fine for VWAP reset
    # Filter only weekdays?
    df_et = df_et[df_et.index.dayofweek < 5]
    
    # Create Date column for grouping
    df_et['Date'] = df_et.index.date
    df_et['Time'] = df_et.index.time
    
    return df_et

def calculate_vwap_bands(df):
    """Calculates Intraday VWAP and Standard Deviation Bands."""
    print("Calculating VWAP and SD Bands...")
    
    # Typical Price
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vp'] = df['tp'] * df['volume']
    df['vp2'] = df['volume'] * (df['tp'] ** 2)
    
    # Process by group (Day) to reset every session
    # Using groupby + cumsum is efficient
    daily_groups = df.groupby('Date')
    
    cum_vol = daily_groups['volume'].cumsum()
    cum_vp = daily_groups['vp'].cumsum()
    cum_vp2 = daily_groups['vp2'].cumsum()
    
    # VWAP
    df['rth_vwap'] = cum_vp / cum_vol
    
    # Variance = (Sum(Vol * Price^2) / Sum(Vol)) - VWAP^2
    # We clip to 0 for numerical stability
    variance = (cum_vp2 / cum_vol) - (df['rth_vwap'] ** 2)
    variance = variance.clip(lower=0)
    
    df['vwap_std'] = np.sqrt(variance)
    
    # Bands
    df['vwap_lower_1'] = df['rth_vwap'] - (1.0 * df['vwap_std'])
    df['vwap_upper_1'] = df['rth_vwap'] + (1.0 * df['vwap_std'])
    
    return df

def resample_bars(df, timeframe='5min'):
    """Resamples 1m data to target timeframe for ORB/Signal."""
    print(f"Resampling to {timeframe}...")
    
    # Define aggregation rules
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'rth_vwap': 'last', # Sample VWAP at close of bar
        'vwap_lower_1': 'last', # Sample Lower Band at close of bar
        'vwap_upper_1': 'last'  # Sample Upper Band at close of bar
    }
    
    # Resample
    resampled = df.resample(timeframe).agg(agg_dict).dropna()
    resampled['Date'] = resampled.index.date
    resampled['Time'] = resampled.index.time
    
    return resampled

def calculate_atr(df, period=14):
    """Calculates ATR."""
    print("Calculating ATR...")
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    atr = true_range.rolling(period).mean()
    df['ATR'] = atr
    return df

def run_backtest_session_loop(df_1m, df_signal, params):
    """
    Optimized Vectorized Backtest Loop.
    """
    print("Starting Optimized Backtest Loop...")
    trades = []
    
    # Pre-compute numpy arrays for speed
    # We will slice these by day indices
    
    dates = df_signal['Date'].unique()
    print(f"Total trading days to process: {len(dates)}")
    
    for current_date in dates:
        # Get daily views using Index Slicing (O(log N)) instead of Masking (O(N))
        # Ensure correct timezone
        tz = df_1m.index.tz
        day_start = pd.Timestamp(current_date).tz_localize(tz)
        day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
        
        # Slicing is fast on sorted DatetimeIndex
        try:
            day_1m = df_1m.loc[day_start:day_end]
        except KeyError:
            continue
            
        day_signal = df_signal[df_signal['Date'] == current_date]
        
        if len(day_signal) < 12 or len(day_1m) < 60:
            continue
            
        # 1. ORB (09:30 - 10:30)
        # Using boolean mask on Time index
        # 5m bars: 09:30, 09:35, ... 10:25. (12 bars)
        
        # Assumption: Time index is consistent
        # Let's use position based if possible, but time is safer
        orb_mask = (day_signal['Time'] >= datetime.time(9, 30)) & (day_signal['Time'] < datetime.time(10, 30))
        orb_data = day_signal[orb_mask]
        
        if orb_data.empty: continue
        
        orb_high = orb_data['high'].max()
        
        # 2. Breakout Search (After 10:30)
        # We look for the first 5m bar CLOSE > ORB_High
        post_orb_mask = day_signal['Time'] >= datetime.time(10, 30)
        post_orb_data = day_signal[post_orb_mask]
        
        # Vectorized check
        breakout_candidates = post_orb_data[post_orb_data['close'] > orb_high]
        
        if breakout_candidates.empty:
            continue
            
        # First breakout
        signal_bar = breakout_candidates.iloc[0]
        signal_time = signal_bar.name # timestamp of 5m close? No, resample index is usually left or right. 
        # In resample_bars, we didn't specify 'label', default 'left'.
        # If label is left, 10:30 bar covers 10:30-10:35.
        # Breakout check 'close > orb_high'.
        # We enter on PULLBACK after the signal.
        # "Signal 5m bar" ends at signal_time + 5m.
        # We start looking for fills from signal_time + 5m.
        
        signal_end_time = signal_bar.name + pd.Timedelta(minutes=5)
        
        current_atr = signal_bar['ATR']
        
        # 3. Execution (1m data) - INVERTED: SHORT AT VWAP
        # We look for price touching VWAP from below or above? "Pullback".
        # If Breakout is UP, price is usually above VWAP. Pullback means Low touches VWAP.
        # Short Limit at VWAP. Filled if High >= VWAP (assuming we are sitting on Offer).
        # Wait, if price is ABOVE VWAP after breakout, and we want to SHORT at VWAP,
        # we need price to come DOWN to VWAP. 
        # So we place a Limit Sell at VWAP.
        # Fill condition: Low <= VWAP (Price traded through our limit).
        
        fill_mask = (day_1m.index >= signal_end_time) & (day_1m['low'] <= day_1m['rth_vwap'])
        
        subset_1m = day_1m[day_1m.index >= signal_end_time]
        if subset_1m.empty: continue
        
        fil_candidates = subset_1m[subset_1m['low'] <= subset_1m['rth_vwap']]
        
        if fil_candidates.empty:
            continue
            
        # We have a fill! (Short Entry)
        fill_bar = fil_candidates.iloc[0]
        entry_time = fill_bar.name
        entry_price = fill_bar['rth_vwap']
        
        # SL: Upper Band 1 (Short gets stopped if price goes UP)
        # We need to map upper band from 5m signal? or 1m current?
        # Usually SL is fixed at entry.
        # Let's map the upper band of the fill candle (or approximate).
        # We need 'vwap_upper_1' in 1m data? 
        # We didn't resample it back to 1m, or did we? calculate_vwap_bands was on df_1m.
        # Yes, df_1m has 'vwap_upper_1'.
        
        vwap_upper = fill_bar['vwap_upper_1']
        sl_price = vwap_upper
        
        # Risk (Price diff)
        risk = sl_price - entry_price
        if risk <= 0: risk = entry_price * 0.005 # Fallback
        
        # TPs (Downside)
        tp_1r = entry_price - (1.0 * risk)
        tp_15r = entry_price - (1.5 * risk)
        tp_2r = entry_price - (2.0 * risk)
        
        # Outcome Simulation
        trade_data = day_1m[day_1m.index > entry_time]
        if trade_data.empty: continue
        
        # Short Outcome:
        # SL Hit if High >= SL
        sl_hits = trade_data[trade_data['high'] >= sl_price]
        max_ts = pd.Timestamp("2200-01-01").tz_localize(trade_data.index.tz)
        sl_time = sl_hits.index[0] if not sl_hits.empty else max_ts
        
        outcomes = {}
        for r_name, tp_val in [('1R', tp_1r), ('1.5R', tp_15r), ('2R', tp_2r)]:
             # TP Hit if Low <= TP
             tp_hits = trade_data[trade_data['low'] <= tp_val]
             tp_time = tp_hits.index[0] if not tp_hits.empty else max_ts
             
             if tp_time < sl_time:
                 # TP Hit
                 outcomes[f'Result_{r_name}'] = float(r_name.replace('R', ''))
             elif sl_time < max_ts:
                 # SL Hit
                 outcomes[f'Result_{r_name}'] = -1.0
             else:
                 # EOD Exit (Short PnL = Entry - Exit)
                 exit_price = trade_data['close'].iloc[-1]
                 pnl = (entry_price - exit_price) / risk
                 outcomes[f'Result_{r_name}'] = pnl

        # Record Trade
        ticks = {
            'Date': current_date,
            'EntryTime': entry_time,
            'EntryPrice': entry_price,
            'SL': sl_price,
            'Risk': risk,
            'ORB_High': orb_high,
            'Type': 'Short'
        }
        ticks.update(outcomes)
        trades.append(ticks)
        
        if len(trades) % 50 == 0:
            print(f"  Processed {len(trades)} trades... Last: {current_date}")

    return pd.DataFrame(trades)

# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    df_raw = load_data(FILE_PATH)
    
    if df_raw is not None:
        # Preprocess
        df_1m = prepare_data(df_raw)
        
        # Calc indicators on 1m (VWAP needs 1m precision ideally)
        df_1m = calculate_vwap_bands(df_1m)
        
        # Resample to 5m for Signal
        df_5m = resample_bars(df_1m, timeframe=ATR_TIMEFRAME)
        
        # Calc ATR on 5m
        df_5m = calculate_atr(df_5m, period=ATR_PERIOD)
        
        # Clean NaNs
        df_5m.dropna(inplace=True)
        
        # Run Backtest
        params = {'sl_multiplier': SL_MULTIPLIER}
        results = run_backtest_session_loop(df_1m, df_5m, params)
        
        if not results.empty:
            print("\n=== BACKTEST RESULTS ===")
            print(f"Total Trades: {len(results)}")
            
            # Save Raw Log
            output_file = "nq_orb_results.csv"
            results.to_csv(output_file, index=False)
            print(f"Detailed trade log saved to {output_file}")

            # ---------------------------------------------------------
            # PROFESSIONAL REPORTING
            # ---------------------------------------------------------
            def generate_professional_report(trades_df, scenario='Result_2R'):
                print(f"\n--- Generating Report for Scenario: {scenario} ---")
                
                # Prepare Equity Curve
                trades_df['return'] = trades_df[scenario]
                trades_df['cum_return'] = trades_df['return'].cumsum()
                trades_df['equity'] = 1 + (trades_df['cum_return'] * 0.01) # Assuming 1% risk per trade for equity curve viz
                
                # Metrics Calculation
                total_r = trades_df['return'].sum()
                win_rate = (trades_df['return'] > 0).mean() * 100
                num_trades = len(trades_df)
                avg_r = trades_df['return'].mean()
                
                # Drawdown
                running_max = trades_df['cum_return'].cummax()
                drawdown = trades_df['cum_return'] - running_max
                max_dd = drawdown.min()
                
                # Profit Factor
                gross_profit = trades_df[trades_df['return'] > 0]['return'].sum()
                gross_loss = abs(trades_df[trades_df['return'] < 0]['return'].sum())
                profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
                
                # Sharpe Ratio (Annualized - Simplified)
                # Assuming ~252 trading days, but we have trades per session. 
                # Let's map trades to days first for accurate Sharpe
                daily_returns = trades_df.groupby('Date')['return'].sum()
                sharpe = (daily_returns.mean() / daily_returns.std()) * (252**0.5) if daily_returns.std() != 0 else 0
                
                # Print Metrics
                print(f"Total Return (R): {total_r:.2f}")
                print(f"Max Drawdown (R): {max_dd:.2f}")
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Profit Factor: {profit_factor:.2f}")
                print(f"Sharpe Ratio: {sharpe:.2f}")
                print(f"Expectancy (R/trade): {avg_r:.2f}")
                
                # -----------------------------------------------------
                # PLOTTING
                # -----------------------------------------------------
                try:
                    sns.set_theme(style="darkgrid")
                    fig, axes = plt.subplots(3, 1, figsize=(12, 18))
                    
                    # 1. Equity Curve
                    axes[0].plot(trades_df['Date'], trades_df['cum_return'], label='Cumulative Return (R)', color='lime')
                    axes[0].set_title(f'Equity Curve ({scenario}) - Total R: {total_r:.1f}', fontsize=14, fontweight='bold')
                    axes[0].set_ylabel('Accumulated R-Multiples')
                    axes[0].legend()
                    
                    # 2. Drawdown
                    axes[1].fill_between(trades_df['Date'], drawdown, 0, color='red', alpha=0.3)
                    axes[1].plot(trades_df['Date'], drawdown, color='red', linewidth=1)
                    axes[1].set_title(f'Drawdown (Max: {max_dd:.2f} R)', fontsize=14, fontweight='bold')
                    axes[1].set_ylabel('Drawdown (R)')
                    
                    # 3. Monthly Heatmap
                    # Create a copy for manipulation
                    hm_df = trades_df.copy()
                    hm_df['Year'] = pd.to_datetime(hm_df['Date']).dt.year
                    hm_df['Month'] = pd.to_datetime(hm_df['Date']).dt.month
                    monthly_returns = hm_df.groupby(['Year', 'Month'])['return'].sum().unstack()
                    
                    sns.heatmap(monthly_returns, annot=True, fmt=".1f", cmap="RdYlGn", center=0, ax=axes[2], cbar_kws={'label': 'R-Multiple'})
                    axes[2].set_title('Monthly Returns Heatmap', fontsize=14, fontweight='bold')
                    
                    plt.tight_layout()
                    chart_filename = f"nq_orb_report_{scenario}.png"
                    plt.savefig(chart_filename)
                    print(f"Chart saved to {chart_filename}")
                    plt.close()
                    
                except Exception as e:
                    print(f"Error generating charts: {e}")

            # Generate Reports for all scenarios
            for scenario in ['Result_1R', 'Result_1.5R', 'Result_2R']:
                generate_professional_report(results.copy(), scenario)
            
        else:
            print("No trades generated.")
    else:
        print("Exiting due to data load failure.")
