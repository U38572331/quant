import pandas as pd
import numpy as np
from itertools import product

# ==========================================
# ─── CONFIG ───
# ==========================================
FILE_PATH = r'C:\Users\user\.gemini\antigravity\scratch\ny_orb_analysis\glbx-mdp3-20100606-20191231.ohlcv-1m.csv'

# Optimization Ranges (Grid Search)
KEY_VALUES = [1, 2, 3, 4]
ATR_PERIODS = [10, 14]
EXIT_SETTINGS = [
    {'tp': 1.5, 'sl': 1.0}, # Scalp
    {'tp': 2.0, 'sl': 1.5}, # Balanced
    {'tp': 3.0, 'sl': 2.0}, # Swing
]
EMA_LENGTH = 200

# ==========================================
# ─── INDICATOR UTILS ───
# ==========================================
def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calc_atr(high, low, close, length):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def calc_vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum()

# ==========================================
# ─── STRATEGY LOGIC ───
# ==========================================
def run_backtest(df, key_val, atr_period, tp_mult, sl_mult):
    df = df.copy()
    
    # 1. Indicators
    df['ATR'] = calc_atr(df['high'], df['low'], df['close'], atr_period)
    df['nLoss'] = key_val * df['ATR']
    df['EMA'] = calc_ema(df['close'], EMA_LENGTH)
    df['VWAP'] = calc_vwap(df['high'], df['low'], df['close'], df['volume'])
    
    # 2. UT Trailing Stop Logic (Stateful)
    src = df['close'].values
    nLoss = df['nLoss'].values
    
    ts_limit = len(df)
    ts_stop = np.zeros(ts_limit)
    pos = np.zeros(ts_limit)
    
    # Initialize Stop
    # Iterate from 1 to end
    for i in range(1, ts_limit):
        price = src[i]
        prev_price = src[i-1]
        loss = nLoss[i]
        prev_s = ts_stop[i-1]
        
        if np.isnan(loss): 
            ts_stop[i] = price
            continue
            
        if (price > prev_s) and (prev_price > prev_s):
            ts_stop[i] = max(prev_s, price - loss)
        elif (price < prev_s) and (prev_price < prev_s):
            ts_stop[i] = min(prev_s, price + loss)
        elif (price > prev_s):
            ts_stop[i] = price - loss
        else:
            ts_stop[i] = price + loss
            
    df['TraillStop'] = ts_stop
    
    # 3. Position Logic
    for i in range(1, ts_limit):
        price = src[i]
        prev_price = src[i-1]
        prev_s = ts_stop[i-1]
        
        if (prev_price < prev_s) and (price > prev_s):
            pos[i] = 1
        elif (prev_price > prev_s) and (price < prev_s):
            pos[i] = -1
        else:
            pos[i] = pos[i-1]
            
    df['Pos'] = pos

    # 4. Filter Features
    df['StratDist'] = (df['close'] - df['TraillStop']) / df['ATR']
    df['AtrVol'] = (df['ATR'] / df['close']) * 100
    
    vol_filter = (df['AtrVol'] > 0.02)
    strat_fresh = (df['StratDist'] > 0.1) & (df['StratDist'] < 5)
    
    trend_long = (df['close'] > df['EMA']) & (df['close'] > df['VWAP'])
    trend_short = (df['close'] < df['EMA']) & (df['close'] < df['VWAP'])
    
    # Signals
    df['Buy_Raw'] = (df['Pos'] == 1) & (df['Pos'].shift(1) != 1)
    df['Sell_Raw'] = (df['Pos'] == -1) & (df['Pos'].shift(1) != -1)
    
    # Final Entry
    df['Buy'] = df['Buy_Raw'] & trend_long & vol_filter & strat_fresh
    df['Sell'] = df['Sell_Raw'] & trend_short & vol_filter & strat_fresh
    
    # 5. Simulation
    trades = []
    in_pos = False
    entry_val = 0.0
    entry_atr = 0.0
    mode = 0 # 1 long, -1 short
    
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    atrs = df['ATR'].values
    buy_sigs = df['Buy'].values
    sell_sigs = df['Sell'].values
    
    for i in range(ts_limit):
        if not in_pos:
            if buy_sigs[i]:
                in_pos = True
                mode = 1
                entry_val = closes[i]
                entry_atr = atrs[i]
            elif sell_sigs[i]:
                in_pos = True
                mode = -1
                entry_val = closes[i]
                entry_atr = atrs[i]
        else:
            # Exit
            curr_h = highs[i]
            curr_l = lows[i]
            
            if mode == 1:
                tp = entry_val + (entry_atr * tp_mult)
                sl = entry_val - (entry_atr * sl_mult)
                
                if curr_l <= sl:
                    pnl = (sl - entry_val) / entry_val
                    trades.append(pnl)
                    in_pos = False
                elif curr_h >= tp:
                    pnl = (tp - entry_val) / entry_val
                    trades.append(pnl)
                    in_pos = False
            else:
                tp = entry_val - (entry_atr * tp_mult)
                sl = entry_val + (entry_atr * sl_mult)
                
                if curr_h >= sl:
                    pnl = (entry_val - sl) / entry_val
                    trades.append(pnl)
                    in_pos = False
                elif curr_l <= tp:
                    pnl = (entry_val - tp) / entry_val
                    trades.append(pnl)
                    in_pos = False
                    
    return trades

def main():
    try:
        print(f"Loading data from {FILE_PATH}...")
        try:
             df = pd.read_csv(FILE_PATH)
        except Exception as e:
             print(f"ERROR: Could not read CSV. {e}")
             return

        df.columns = [c.lower().strip() for c in df.columns]
        
        req_cols = ['close', 'high', 'low', 'volume', 'symbol']
        if not all(c in df.columns for c in req_cols):
             # Try without symbol if missing, but we suspect it's there
             if 'symbol' not in df.columns:
                 print("WARNING: 'symbol' column not found. Assuming single instrument.")
             else:
                 pass
        
        # Filter for primary symbol
        if 'symbol' in df.columns:
            # Find most common symbol
            primary_sym = df['symbol'].mode()[0]
            print(f"Detected multiple symbols. Filtering for primary: {primary_sym}")
            df = df[df['symbol'] == primary_sym].copy()
            
        print(f"Data Loaded: {len(df)} rows")
        
        # Sort by time if needed (assuming sorted but good to ensure)
        # Check for time column 'ts_event' or similar
        if 'ts_event' in df.columns:
            df['ts_event'] = pd.to_datetime(df['ts_event'])
            df = df.sort_values('ts_event')
        
        # Limit rows for speed
        if len(df) > 500000:
            print("Truncating to last 500,000 bars for performance...")
            df = df.iloc[-500000:].reset_index(drop=True)

        print("Running Grid Search Optimization...")
        
        results = []
        for kv, atr, exit_s in product(KEY_VALUES, ATR_PERIODS, EXIT_SETTINGS):
            print(f"Testing: K={kv}, ATR={atr}, TP={exit_s['tp']}")
            trades = run_backtest(df, kv, atr, exit_s['tp'], exit_s['sl'])
            
            if not trades: 
                continue
            
            win_cnt = len([t for t in trades if t > 0])
            count = len(trades)
            wr = (win_cnt / count) * 100
            net_pnl = sum(trades) * 100
            
            results.append({
                'Key Value': kv,
                'ATR Period': atr,
                'TP Mult': exit_s['tp'],
                'SL Mult': exit_s['sl'],
                'Trades': count,
                'Win Rate %': round(wr, 2),
                'Net PnL %': round(net_pnl, 2)
            })
            
        if not results:
            print("No trades found.")
            return
            
        res_df = pd.DataFrame(results).sort_values('Net PnL %', ascending=False)
        print("\n=== TOP 5 CONFIGURATIONS ===")
        print(res_df.head(5).to_string(index=False))
        
        with open('optimization_report.md', 'w') as f:
            f.write("# Optimization Report\n\n")
            f.write("```\n")
            f.write(res_df.to_string(index=False))
            f.write("\n```\n")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
