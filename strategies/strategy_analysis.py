import pandas as pd
import numpy as np
from datetime import time
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_score
import os

# Configuration
DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\data.csv"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Parameters
RTH_START = time(9, 30)
RTH_END = time(16, 15)
ORB_END = time(9, 45) # 15 minute ORB

def load_and_prep_data(path):
    print(f"Loading data from {path}...")
    try:
        df = pd.read_csv(path)
        
        # Standardize column names
        df.columns = [c.capitalize() for c in df.columns]
        # Expected: Timestamp, Open, High, Low, Close, Volume, Symbol
        
        if 'Timestamp' not in df.columns:
            # Fallback if lowercase
            df.columns = [c.lower() for c in df.columns]
            if 'timestamp' in df.columns:
                df = df.rename(columns={'timestamp': 'Timestamp'})
        
        # FIx weird format: 2010-06-06T22_00_00.000000000Z -> replace _ with :
        # Note: We only replace the _ in the time part.
        # Actually, simpler to just replace all _ with : in the timestamp column string before parsing
        df['Timestamp'] = pd.to_datetime(df['Timestamp'].astype(str).str.replace('_', ':'))
        
        # Handle multiple symbols: Select most liquid contract per minute
        print("Aggregating contracts (selecting max volume per minute)...")
        # We assume indices are clean enough that max volume implies the front month active contract
        # This is a standard simple roll stitch method
        df = df.sort_values(['Timestamp', 'Volume'], ascending=[True, False])
        df = df.drop_duplicates(subset=['Timestamp'], keep='first')
        
        df = df.set_index('Timestamp').sort_index()
        
        # Localize/Convert Timezone
        # Input looks like zulu 'Z'.
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        df = df.tz_convert('US/Eastern')
        
        # Clean
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
        
        # Add date column for grouping
        df['Date'] = df.index.date
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def run_strategy(df):
    print("Running strategy simulation...")
    
    # Pre-calc ATR
    df['ATR'] = calculate_atr(df)
    
    daily_groups = df.groupby('Date')
    
    trades = []
    
    # We iterate days
    for date, day_data in daily_groups:
        if len(day_data) < 30: continue 
        
        # Define Segments
        orb_data = day_data.between_time(RTH_START, ORB_END)
        if orb_data.empty: continue
        
        # ORB Levels
        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_mid = (orb_high + orb_low) / 2
        orb_range = orb_high - orb_low
        
        if orb_range == 0: continue

        post_orb_data = day_data.between_time(ORB_END, RTH_END)
        if post_orb_data.empty: continue
        
        # Identify Breakout
        # Simple Logic: First 1m Close outside ORB
        entry_time = None
        direction = 0 # 1=Long, -1=Short
        entry_price = 0
        
        for t, row in post_orb_data.iterrows():
            if row['Close'] > orb_high:
                direction = 1
                entry_price = row['Close']
                entry_time = t
                break
            elif row['Close'] < orb_low:
                direction = -1
                entry_price = row['Close']
                entry_time = t
                break
                
        if direction == 0:
            continue
            
        # Features for ML
        # 1. Gap (Requires Prev Day Close - approximate with first open if needed or store/shift)
        # 2. ORB Range %
        # 3. Volume
        
        # Calculate Exits (Vectorized for multiple SL/TP strategies)
        trade_base = {
            'EntryTime': entry_time,
            'Date': date,
            'Direction': direction,
            'EntryPrice': entry_price,
            'ORBHeight': orb_range,
            'ATR': day_data.loc[entry_time]['ATR'],
            'GridVolume': day_data.loc[entry_time]['Volume']
        }
        
        # Simulation of various strategies
        # SL Modes: 
        #   - Opposite (ORB High/Low)
        #   - Midpoint (ORB Mid)
        #   - Tight (Entry candle low/high - hard to get from here without preserving candles, will skip for speed or use 0.25 ORB)
        #   - ATR (1.0, 1.5, 2.0)
        # TP Modes:
        #   - R-multiples (1, 1.5, 2, 3, 5, 10, EOD)
        
        atr = trade_base['ATR'] if not pd.isna(trade_base['ATR']) else orb_range
        
        sl_levels = {
            'Opposite': orb_low if direction == 1 else orb_high,
            'Midpoint': orb_mid,
            'ATR_1.0': entry_price - (1.0 * atr * direction),
            'ATR_1.5': entry_price - (1.5 * atr * direction),
            'ORB_0.5': entry_price - (0.5 * orb_range * direction)
        }
        
        # Pre-scan the path to find Hit times for prices
        # Optimization: Calculate Highs/Lows relative to Entry
        # Long: Highs > TP, Lows < SL
        path = post_orb_data.loc[entry_time:].iloc[1:] # steps after entry
        if path.empty: continue
        
        path_lows = path['Low'].values
        path_highs = path['High'].values
        path_closes = path['Close'].values
        
        for sl_name, sl_price in sl_levels.items():
            # Calculate Risk
            risk = abs(entry_price - sl_price)
            if risk <= 0: continue
            
            # Find Index of SL Hit
            if direction == 1:
                sl_hits = np.where(path_lows <= sl_price)[0]
            else:
                sl_hits = np.where(path_highs >= sl_price)[0]
                
            first_sl_idx = sl_hits[0] if len(sl_hits) > 0 else len(path)
            
            # Test TPs
            tp_r_multiples = [1, 1.5, 2, 3, 5, 10]
            
            for r in tp_r_multiples:
                tp_dist = risk * r
                tp_price = entry_price + (tp_dist * direction)
                
                # Find Index of TP Hit
                if direction == 1:
                    tp_hits = np.where(path_highs >= tp_price)[0]
                else:
                    tp_hits = np.where(path_lows <= tp_price)[0]
                    
                first_tp_idx = tp_hits[0] if len(tp_hits) > 0 else len(path)
                
                # Result
                res = {}
                if first_sl_idx < first_tp_idx:
                    # SL Hit
                    pnl = -risk
                    res_type = 'SL'
                    exit_idx = first_sl_idx
                elif first_tp_idx < first_sl_idx:
                    # TP Hit
                    pnl = tp_dist # (TP - Entry)*Dir = risk*r
                    res_type = 'TP'
                    exit_idx = first_tp_idx
                else:
                    # Neither hit -> EOD
                    # PnL = (LastClose - Entry) * Dir
                    # Actually, if neither hit, index is len(path), which means we ran out of data
                    # Use last close
                    final_close = path_closes[-1]
                    pnl = (final_close - entry_price) * direction
                    res_type = 'EOD'
                
                trade_res = trade_base.copy()
                trade_res['SL_Type'] = sl_name
                trade_res['TP_R'] = r
                trade_res['PnL'] = pnl
                trade_res['Result'] = res_type
                trades.append(trade_res)
                
    return pd.DataFrame(trades)

def optimize_and_ml(trades_df):
    if trades_df.empty:
        print("No trades available for optimization.")
        return
        
    print("\n--- Strategy Optimization ---")
    
    # 1. Identify Best Raw Parameters (SL/TP) on Training Data
    # Split by Date to avoid lookahead
    dates = trades_df['Date'].unique()
    train_dates, test_dates = train_test_split(dates, test_size=0.3, shuffle=False)
    
    train_df = trades_df[trades_df['Date'].isin(train_dates)]
    test_df = trades_df[trades_df['Date'].isin(test_dates)]
    
    # Group by (SL_Type, TP_R)
    stats = train_df.groupby(['SL_Type', 'TP_R'])['PnL'].sum().reset_index()
    best_config = stats.loc[stats['PnL'].idxmax()]
    
    print(f"Best Raw Configuration (Train Set): SL={best_config['SL_Type']}, TP={best_config['TP_R']}R")
    
    # 2. Apply ML to Best Configuration
    # Filter dataset to just this config
    subset_train = train_df[(train_df['SL_Type'] == best_config['SL_Type']) & (train_df['TP_R'] == best_config['TP_R'])].copy()
    subset_test = test_df[(test_df['SL_Type'] == best_config['SL_Type']) & (test_df['TP_R'] == best_config['TP_R'])].copy()
    
    # Target: Profitable Trade?
    subset_train['Target'] = (subset_train['PnL'] > 0).astype(int)
    subset_test['Target'] = (subset_test['PnL'] > 0).astype(int)
    
    # Features (Simple subset)
    # Note: In a real expanded version, we'd add more features (moving averages, rsi, etc.) earlier
    features = ['ORBHeight', 'ATR', 'GridVolume'] 
    
    rf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42, class_weight='balanced')
    rf.fit(subset_train[features], subset_train['Target'])
    
    # Evaluate
    train_preds = rf.predict(subset_train[features])
    test_preds = rf.predict(subset_test[features])
    
    print("\nML Performance on Test Set (Best Config):")
    print(classification_report(subset_test['Target'], test_preds))
    
    # Equity Curve Comparison
    # 1. All Trades (Best Config)
    # 2. ML Filtered Trades (Best Config + Prediction=1)
    
    full_equity = subset_test['PnL'].cumsum()
    
    filtered_test = subset_test[test_preds == 1]
    filtered_equity = filtered_test['PnL'].cumsum()
    
    plt.figure(figsize=(10,6))
    plt.plot(full_equity.reset_index(drop=True), label='Raw Strategy (Best Params)')
    plt.plot(filtered_equity.reset_index(drop=True), label='ML Filtered')
    plt.title(f"Equity Curve: SL {best_config['SL_Type']} TP {best_config['TP_R']}R")
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, 'equity_curve_comparison.png'))
    print(f"Equity curve saved to {os.path.join(OUTPUT_DIR, 'equity_curve_comparison.png')}")

    # Feature Importance
    imps = rf.feature_importances_
    print("\nFeature Importance:")
    for f, i in zip(features, imps):
        print(f"{f}: {i:.4f}")

def main():
    df = load_and_prep_data(DATA_PATH)
    if df is None: return
    
    trades = run_strategy(df)
    trades.to_csv(os.path.join(OUTPUT_DIR, 'opt_trades.csv'))
    
    optimize_and_ml(trades)

if __name__ == "__main__":
    main()
