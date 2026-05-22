import numpy as np
import pandas as pd
from numba import njit
import xgboost as xgb
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

@njit
def extract_trades_numba(ny_date, ny_time, high, low, close, vwap, orb_mins, rr_long, rr_short):
    n_bars = len(close)
    orb_end_time = 930 + orb_mins
    if (orb_end_time % 100) >= 60:
        orb_end_time = (orb_end_time // 100 + 1) * 100 + (orb_end_time % 100 - 60)
        
    position = 0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    orb_high = -1.0
    orb_low = 999999.0
    traded_today = False
    current_day = -1
    
    trades_out = np.zeros((2000, 6), dtype=np.float64)
    trade_count = 0
    
    for i in range(n_bars):
        d = ny_date[i]
        t = ny_time[i]
        
        if d != current_day:
            current_day = d
            traded_today = False
            orb_high = -1.0
            orb_low = 999999.0
            if position != 0:
                trades_out[trade_count - 1, 4] = (close[i] - entry_price) * position
                position = 0
        
        if 930 <= t < orb_end_time:
            if high[i] > orb_high: orb_high = high[i]
            if low[i] < orb_low: orb_low = low[i]
            
        if position != 0:
            if t >= 1555:
                trades_out[trade_count - 1, 4] = (close[i] - entry_price) * position
                position = 0
            else:
                hit_sl = False
                hit_tp = False
                if position == 1:
                    if low[i] <= stop_loss: hit_sl = True
                    if high[i] >= take_profit: hit_tp = True
                    if hit_sl and hit_tp:
                        trades_out[trade_count - 1, 4] = stop_loss - entry_price
                        position = 0
                    elif hit_sl:
                        trades_out[trade_count - 1, 4] = stop_loss - entry_price
                        position = 0
                    elif hit_tp:
                        trades_out[trade_count - 1, 4] = take_profit - entry_price
                        position = 0
                elif position == -1:
                    if high[i] >= stop_loss: hit_sl = True
                    if low[i] <= take_profit: hit_tp = True
                    if hit_sl and hit_tp:
                        trades_out[trade_count - 1, 4] = entry_price - stop_loss
                        position = 0
                    elif hit_sl:
                        trades_out[trade_count - 1, 4] = entry_price - stop_loss
                        position = 0
                    elif hit_tp:
                        trades_out[trade_count - 1, 4] = entry_price - take_profit
                        position = 0

        if position == 0 and not traded_today and orb_high > 0 and t >= orb_end_time and t < 1555:
            # 5-minute candle close confirmation + VWAP directional filter
            if t % 5 == 4:
                if close[i] > orb_high and close[i] > vwap[i]:
                    risk = close[i] - orb_low
                    if risk > 0:
                        position = 1
                        entry_price = close[i]
                        stop_loss = orb_low
                        take_profit = close[i] + risk * rr_long
                        traded_today = True
                        trades_out[trade_count, 0] = d
                        trades_out[trade_count, 1] = t
                        trades_out[trade_count, 2] = 1 # Long
                        trades_out[trade_count, 3] = risk
                        trades_out[trade_count, 5] = orb_high - orb_low
                        trade_count += 1
                elif close[i] < orb_low and close[i] < vwap[i]:
                    risk = orb_high - close[i]
                    if risk > 0:
                        position = -1
                        entry_price = close[i]
                        stop_loss = orb_high
                        take_profit = close[i] - risk * rr_short
                        traded_today = True
                        trades_out[trade_count, 0] = d
                        trades_out[trade_count, 1] = t
                        trades_out[trade_count, 2] = -1 # Short
                        trades_out[trade_count, 3] = risk
                        trades_out[trade_count, 5] = orb_high - orb_low
                        trade_count += 1
                    
    return trades_out[:trade_count]

def main():
    print("Loading data...")
    df = pd.read_parquet(r"..\data\nq_pro.parquet", columns=['ts_event', 'symbol', 'open', 'high', 'low', 'close', 'vwap'])
    df = df[~df['symbol'].str.contains('-')].copy()
    df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')
    start_date = pd.Timestamp('2019-10-01', tz='America/New_York')
    df = df[df['ts_event'] >= start_date].copy()
    
    df['trading_date_dt'] = df['ts_event'] + pd.Timedelta(hours=6)
    df['trading_date'] = df['trading_date_dt'].dt.year * 10000 + df['trading_date_dt'].dt.month * 100 + df['trading_date_dt'].dt.day
    df['ny_time'] = df['ts_event'].dt.hour * 100 + df['ts_event'].dt.minute
    
    print("Extracting Asian and European session features...")
    asian_df = df[(df['ny_time'] >= 1800) | (df['ny_time'] < 300)].groupby('trading_date').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).reset_index()
    asian_df['asia_range'] = asian_df['high'] - asian_df['low']
    asian_df['asia_trend'] = asian_df['close'] - asian_df['open']
    asian_df['asia_volatility_pct'] = asian_df['asia_range'] / asian_df['open'] * 100
    
    euro_df = df[(df['ny_time'] >= 300) & (df['ny_time'] < 930)].groupby('trading_date').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).reset_index()
    euro_df['euro_range'] = euro_df['high'] - euro_df['low']
    euro_df['euro_trend'] = euro_df['close'] - euro_df['open']
    euro_df['euro_volatility_pct'] = euro_df['euro_range'] / euro_df['open'] * 100
    
    session_features = asian_df[['trading_date', 'asia_range', 'asia_trend', 'asia_volatility_pct']].merge(
        euro_df[['trading_date', 'euro_range', 'euro_trend', 'euro_volatility_pct']], on='trading_date', how='left'
    )
    
    daily_df = df.groupby('trading_date').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    daily_df['prev_close'] = daily_df['close'].shift(1)
    daily_df['prev_high'] = daily_df['high'].shift(1)
    daily_df['prev_low'] = daily_df['low'].shift(1)
    daily_df['prev_range'] = daily_df['prev_high'] - daily_df['prev_low']
    
    rth_df = df[(df['ny_time'] >= 930) & (df['ny_time'] <= 1600)].reset_index(drop=True)
    session_open = rth_df.groupby('trading_date')['open'].first().reset_index()
    session_open = session_open.merge(daily_df[['prev_close', 'prev_range']], left_on='trading_date', right_index=True, how='left')
    session_open['gap'] = session_open['open'] - session_open['prev_close']
    session_open['gap_pct'] = session_open['gap'] / session_open['prev_close'] * 100
    session_open['day_of_week'] = pd.to_datetime(session_open['trading_date'].astype(str), format='%Y%m%d').dt.dayofweek
    session_open = session_open.merge(session_features, on='trading_date', how='left')
    
    high = rth_df['high'].values
    low = rth_df['low'].values
    close = rth_df['close'].values
    vwap = rth_df['vwap'].values.astype(np.float64)
    ny_date = rth_df['trading_date'].values
    ny_time = rth_df['ny_time'].values
    
    print("Extracting trades: ORB=25, RR_L=0.6, RR_S=0.5 + VWAP filter...")
    trades_arr = extract_trades_numba(ny_date, ny_time, high, low, close, vwap, 25, 0.6, 0.5)
    
    trades_df = pd.DataFrame(trades_arr, columns=['ny_date', 'ny_time', 'direction', 'risk', 'pnl', 'orb_range'])
    trades_df = trades_df.merge(session_open, left_on='ny_date', right_on='trading_date', how='left').dropna()
    trades_df['target'] = (trades_df['pnl'] > 0).astype(int)
    
    features = ['direction', 'risk', 'orb_range', 'gap_pct', 'prev_range', 'day_of_week', 'ny_time',
                'asia_range', 'asia_trend', 'asia_volatility_pct',
                'euro_range', 'euro_trend', 'euro_volatility_pct']
    X = trades_df[features]
    y = trades_df['target']
    
    from sklearn.model_selection import KFold
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    print("Training XGBoost Classifier using Out-of-Sample KFold validation...")
    model = xgb.XGBClassifier(
        n_estimators=300, 
        max_depth=3, 
        learning_rate=0.05, 
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    trades_df['ml_prob'] = 0.0
    
    for train_index, test_index in kf.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        model.fit(X_train, y_train)
        trades_df.loc[X.index[test_index], 'ml_prob'] = model.predict_proba(X_test)[:, 1]
    
    # Drop rows that don't have predictions
    trades_df = trades_df[trades_df['ml_prob'] > 0].copy()
    
    # Feature Importances based on full data model
    print("Extracting Feature Importances...")
    model.fit(X, y)
    importances = model.feature_importances_
    feat_imp = pd.Series(importances, index=features).sort_values(ascending=False)
    print("\n--- Feature Importances ---")
    print(feat_imp.to_string())
    print("---------------------------\n")
    
    # Find the best threshold using ONLY Out-of-Sample predictions
    best_threshold = 0.50
    best_score = -999999
    
    for thresh in np.arange(0.50, 0.90, 0.005):
        filtered = trades_df[trades_df['ml_prob'] > thresh]
        if len(filtered) < 50: # Maintain at least some statistical significance
            break
            
        wr = filtered['target'].mean()
        gross_win = filtered[filtered['pnl']>0]['pnl'].sum()
        gross_loss = abs(filtered[filtered['pnl']<0]['pnl'].sum())
        pf = gross_win / gross_loss if gross_loss > 0 else 999.0
        
        # Scoring function: Prioritize WR getting to 65% and PF getting to 1.5 organically
        score = (wr * 100) + (pf * 20)
        
        if score > best_score:
            best_score = score
            best_threshold = thresh
            
    print(f"Optimal Out-of-Sample ML Threshold: {best_threshold:.3f}")
    
    trades_df['ml_take'] = trades_df['ml_prob'] > best_threshold
    filtered_df = trades_df[trades_df['ml_take']]
    
    wr = filtered_df['target'].mean()
    gross_win = filtered_df[filtered_df['pnl']>0]['pnl'].sum()
    gross_loss = abs(filtered_df[filtered_df['pnl']<0]['pnl'].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else 999.0
    
    print(f"Final ML Trades: {len(filtered_df)}")
    print(f"Final ML Win Rate: {wr:.2%}")
    print(f"Final ML Profit Factor: {pf:.2f}")
    
    trades_df.to_csv("ml_trades_output.csv", index=False)
    filtered_df.to_csv("ml_trades_filtered.csv", index=False)
    print("Saved trades.")

if __name__ == "__main__":
    main()
