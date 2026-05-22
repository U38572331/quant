import pandas as pd
import numpy as np
# import pandas_ta as ta
# import optuna
from datetime import datetime
from datetime import datetime

# --- Indicators ---

def heikin_ashi(df):
    heikin_ashi_df = pd.DataFrame(index=df.index)
    heikin_ashi_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    
    # Initialize open with the first open
    heikin_ashi_df['open'] = df['open']
    # Iterate to calculate HA open (slow, need vectorization optimization later if slow)
    # Vectorized approximation or Numba if needed. For now, simple loop for correctness or shifted.
    # HA_Open = (Previous HA_Open + Previous HA_Close) / 2
    # Efficient pandas way:
    ha_open = [df['open'].iloc[0]]
    ha_close = heikin_ashi_df['close'].values
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_close[i-1]) / 2)
    heikin_ashi_df['open'] = ha_open
    
    heikin_ashi_df['high'] = heikin_ashi_df[['open', 'close']].join(df['high']).max(axis=1)
    heikin_ashi_df['low'] = heikin_ashi_df[['open', 'close']].join(df['low']).min(axis=1)
    return heikin_ashi_df

def ut_bot_alert(df, key_value=1, atr_period=10, use_heikin_ashi=False):
    # UT Bot Strategy
    source = df.copy()
    if use_heikin_ashi:
        source = heikin_ashi(df)
    
    src = source['close']
    
    # ATR Manual Calculation
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # Wilder's Smoothing
    xATR = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    nLoss = key_value * xATR
    
    xATRTrailingStop = np.zeros(len(df))
    
    # Logic for Trailing Stop (Iterative because of self-reference)
    # Using numpy for speed where possible, but this state-dependent logic is tricky to vectorize fully without C/Numba.
    # We'll use a loop for clarity and correctness first.
    src_val = src.values
    nLoss_val = nLoss.values
    ts = np.zeros(len(df))
    
    for i in range(1, len(df)):
        prev_ts = ts[i-1]
        if src_val[i] > prev_ts and src_val[i-1] > prev_ts:
            ts[i] = max(prev_ts, src_val[i] - nLoss_val[i])
        elif src_val[i] < prev_ts and src_val[i-1] < prev_ts:
            ts[i] = min(prev_ts, src_val[i] + nLoss_val[i])
        elif src_val[i] > prev_ts:
            ts[i] = src_val[i] - nLoss_val[i]
        else: # src_val[i] < prev_ts
            ts[i] = src_val[i] + nLoss_val[i]
            
    df['xATRTrailingStop'] = ts
    
    # Position Logic
    pos = np.zeros(len(df))
    for i in range(1, len(df)):
        prev_pos = pos[i-1]
        prev_ts = ts[i-1]
        if src_val[i-1] < prev_ts and src_val[i] > prev_ts:
            pos[i] = 1
        elif src_val[i-1] > prev_ts and src_val[i] < prev_ts:
            pos[i] = -1
        else:
            pos[i] = prev_pos
            
    df['ut_pos'] = pos
    df['ut_buy'] = (df['ut_pos'] == 1) & (df['ut_pos'].shift(1) != 1)
    df['ut_sell'] = (df['ut_pos'] == -1) & (df['ut_pos'].shift(1) != -1)
    return df

def stc_indicator(df, length=12, fast_length=26, slow_length=50):
    # Schaff Trend Cycle
    # STC = 100 * (MA - MACD_Low) / (MACD_High - MACD_Low) ... smoothed
    
    # STC Manual Calculation
    # MACD
    ema_fast = df['close'].ewm(span=fast_length, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_length, adjust=False).mean()
    macd = ema_fast - ema_slow
    
    # Function to calculate Stoch over a series
    def stoch(series, length):
        min_val = series.rolling(length).min()
        max_val = series.rolling(length).max()
        return (series - min_val) / (max_val - min_val) * 100
    
    # STC Logic: 
    # 1. %K of MACD
    stoch_macd = stoch(macd, length)
    # 2. Smooth %K (PF) ? No, STC uses specific recursion.
    # TV Logic: 
    #   p1 = (stoch_macd > 0) ? stoch_macd : 0
    #   pf = (p1*factor) + (prev_pf * (1-factor)) (EMA)
    # But usually STC is:
    #   %K1 = Stoch(MACD)
    #   %D1 = EMA(%K1, length/2?) - No, usually factor 0.5
    #   %K2 = Stoch(%D1)
    #   STC = EMA(%K2, factor 0.5)
    
    # We will use valid approximation:
    # 1. Stoch(MACD)
    k1 = stoch(macd, length).fillna(0)
    # 2. EMA(k1)
    d1 = k1.ewm(alpha=0.5, adjust=False).mean()
    # 3. Stoch(d1)
    k2 = stoch(d1, length).fillna(0)
    # 4. EMA(k2) -> STC
    stc_val = k2.ewm(alpha=0.5, adjust=False).mean()
    
    df['stc'] = stc_val
    return df

# --- Data Loading ---

def load_data(filepath='data.csv'):
    # Adjust names based on file inspection
    df = pd.read_csv(filepath)
    # Assuming standard headers, will adjust after inspection
    # df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    # df['datetime'] = pd.to_datetime(df['datetime'])
    # df.set_index('datetime', inplace=True)
    return df

if __name__ == "__main__":
    try:
        print("Attempting to load data...")
        df = load_data('data.csv')
        print("Data loaded successfully.")
        print("Columns:", df.columns.tolist())
        print("First 5 rows:")
        print(df.head())
        print("Data Info:")
        print(df.info())
    except Exception as e:
        print(f"Error loading data: {e}")

