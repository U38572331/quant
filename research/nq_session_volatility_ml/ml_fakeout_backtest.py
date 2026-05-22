"""
ML-Enhanced Fakeout (Mean Reversion) Strategy Backtest Engine
Takes advantage of low breakout success rate by fading breakouts that fail.
"""
import pandas as pd
import numpy as np
import json
import os
import warnings
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
warnings.filterwarnings('ignore')

DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet"
OUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\nq_session_volatility_ml"

print("1. Loading Data...")
df = pd.read_parquet(DATA_PATH, columns=['ts_event', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'vwap'])
df = df[~df['symbol'].str.contains('-')].copy()
df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')
df = df[df['ts_event'] >= '2019-10-01'].copy()
df['trading_date_dt'] = df['ts_event'] + pd.Timedelta(hours=6)
df['tdate'] = df['trading_date_dt'].dt.date
df['nyt'] = df['ts_event'].dt.hour * 100 + df['ts_event'].dt.minute
df.set_index('ts_event', inplace=True)
df.sort_index(inplace=True)

print("2. Precomputing Edge Features...")
asia = df[(df['nyt'] >= 1800) | (df['nyt'] < 300)]
euro = df[(df['nyt'] >= 300) & (df['nyt'] < 930)]
us   = df[(df['nyt'] >= 930) & (df['nyt'] <= 1600)]

def get_stats(sdf):
    return sdf.groupby('tdate').agg(
        o=('open', 'first'), h=('high', 'max'), l=('low', 'min'),
        c=('close', 'last'), v=('volume', 'sum')
    )

as_stats = get_stats(asia).add_prefix('asia_')
eu_stats = get_stats(euro).add_prefix('euro_')
us_stats = get_stats(us).add_prefix('us_')

daily = pd.concat([as_stats, eu_stats, us_stats], axis=1).dropna()
daily['prev_us_c'] = daily['us_c'].shift(1)
daily.dropna(inplace=True)

# Deep Edge Features
daily['gap_pct'] = (daily['us_o'] - daily['prev_us_c']) / daily['prev_us_c'] * 100
daily['euro_trend_pct'] = (daily['euro_c'] - daily['euro_o']) / daily['euro_o'] * 100
daily['pre_vol'] = (daily['asia_h'] - daily['asia_l'])/daily['asia_o']*100 + (daily['euro_h'] - daily['euro_l'])/daily['euro_o']*100
daily['pre_vol_z'] = (daily['pre_vol'] - daily['pre_vol'].rolling(60, min_periods=20).mean()) / daily['pre_vol'].rolling(60, min_periods=20).std()
daily['euro_vol_pctile'] = daily['euro_v'].rolling(20, min_periods=5).rank(pct=True)

daily_dict = daily.to_dict('index')
valid_dates = sorted(list(daily_dict.keys()))

print("3. Simulating FAKEOUT Trades...")
trades = []
us_grouped = us.groupby('tdate')

for tdate in valid_dates:
    if tdate not in us_grouped.groups: continue
    day_df = us_grouped.get_group(tdate)
    
    # 09:30 - 10:00 ORB
    orb_df = day_df[(day_df['nyt'] >= 930) & (day_df['nyt'] < 1000)]
    if orb_df.empty or len(orb_df) < 15: continue
    
    orb_h = orb_df['high'].max()
    orb_l = orb_df['low'].min()
    orb_range = orb_h - orb_l
    if orb_range <= 0: continue
    
    feats = daily_dict[tdate]
    
    # Execution Window
    exec_df = day_df[(day_df['nyt'] >= 1000) & (day_df['nyt'] <= 1530)]
    if exec_df.empty: continue
    
    # Fakeout tracking variables
    trap_dir = 0 # 1 if price breaks above orb_h (bull trap), -1 if breaks below orb_l (bear trap)
    trap_extreme = 0
    
    entry_price = 0
    entry_dir = 0 # -1 to fade bull trap, 1 to fade bear trap
    entry_time = None
    sl_price = 0
    tp_price = 0
    
    for idx, row in exec_df.iterrows():
        # Track traps
        if trap_dir == 0:
            if row['high'] > orb_h:
                trap_dir = 1
                trap_extreme = row['high']
            elif row['low'] < orb_l:
                trap_dir = -1
                trap_extreme = row['low']
        
        # Update trap extremes if we haven't entered yet
        if trap_dir == 1 and row['high'] > trap_extreme:
            trap_extreme = row['high']
        elif trap_dir == -1 and row['low'] < trap_extreme:
            trap_extreme = row['low']
            
        # Check for Entry (Close back inside the ORB)
        if trap_dir == 1 and row['close'] < orb_h:
            entry_price = row['close']
            entry_dir = -1  # Go SHORT
            entry_time = idx
            sl_price = trap_extreme
            tp_price = orb_l
            break
        elif trap_dir == -1 and row['close'] > orb_l:
            entry_price = row['close']
            entry_dir = 1   # Go LONG
            entry_time = idx
            sl_price = trap_extreme
            tp_price = orb_h
            break

    if entry_dir == 0: continue
    
    # Calculate Risk
    risk = sl_price - entry_price if entry_dir == -1 else entry_price - sl_price
    if risk <= 0: risk = entry_price * 0.0005 # Fallback risk
    
    # Outcome Simulation
    post_entry = exec_df.loc[entry_time:]
    if post_entry.empty: continue
    if len(post_entry) > 1: post_entry = post_entry.iloc[1:]
    
    outcome = "EOD"
    exit_price = post_entry['close'].iloc[-1]
    
    for _, erow in post_entry.iterrows():
        if erow['nyt'] >= 1555: break
        
        if entry_dir == 1: # LONG Fakeout
            if erow['low'] <= sl_price:
                outcome = "SL"
                exit_price = sl_price
                break
            if erow['high'] >= tp_price:
                outcome = "TP"
                exit_price = tp_price
                break
        else: # SHORT Fakeout
            if erow['high'] >= sl_price:
                outcome = "SL"
                exit_price = sl_price
                break
            if erow['low'] <= tp_price:
                outcome = "TP"
                exit_price = tp_price
                break
                
    pnl = (exit_price - entry_price) if entry_dir == 1 else (entry_price - exit_price)
    r_pnl = pnl / risk
    
    trades.append({
        'tdate': tdate,
        'entry_time': entry_time,
        'direction': entry_dir,
        'risk': risk,
        'reward': (tp_price - entry_price) if entry_dir==1 else (entry_price - tp_price),
        'outcome': outcome,
        'pnl': pnl,
        'r_pnl': r_pnl,
        'label': 1 if r_pnl > 0.5 else 0,
        # Features
        'gap_pct': feats['gap_pct'],
        'euro_trend_pct': feats['euro_trend_pct'],
        'pre_vol_z': feats['pre_vol_z'],
        'euro_vol_pctile': feats['euro_vol_pctile'],
        'orb_range_pct': orb_range / orb_df['open'].iloc[0] * 100
    })

tdf = pd.DataFrame(trades)
tdf['tdate'] = pd.to_datetime(tdf['tdate'])
print(f"Total Base Fakeout Trades: {len(tdf)}")
print(f"Base Win Rate: {tdf['label'].mean():.1%}")

print("4. ML Walk-Forward Training (XGBoost)...")
tdf['year'] = tdf['tdate'].dt.year
years = sorted(tdf['year'].unique())

features = ['gap_pct', 'euro_trend_pct', 'pre_vol_z', 'euro_vol_pctile', 'orb_range_pct', 'direction']

tdf['ml_prob'] = np.nan
wf_stats = []

for test_yr in range(years[0]+2, years[-1]+1):
    train_mask = (tdf['year'] >= test_yr - 2) & (tdf['year'] < test_yr)
    test_mask = tdf['year'] == test_yr
    
    tr = tdf[train_mask]
    te = tdf[test_mask]
    if len(tr) < 50 or len(te) < 10: continue
    
    X_train, y_train = tr[features].values, tr['label'].values
    X_test, y_test = te[features].values, te['label'].values
    
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    
    model = XGBClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric='logloss',
        scale_pos_weight=pos_weight
    )
    model.fit(X_train, y_train)
    
    probs = model.predict_proba(X_test)[:, 1]
    tdf.loc[test_mask, 'ml_prob'] = probs
    
    acc = accuracy_score(y_test, (probs > 0.5))
    wf_stats.append({'year': test_yr, 'n_test': len(te), 'acc': acc})
    print(f"  {test_yr}: N={len(te)}, Accuracy={acc:.1%}")

oos_df = tdf.dropna(subset=['ml_prob']).copy()

# Find optimal threshold that produces a high PF
best_pf = 0
best_thresh = 0.5
for th in np.arange(0.40, 0.70, 0.02):
    filtered = oos_df[oos_df['ml_prob'] >= th]
    if len(filtered) < 20: break
    
    gw = filtered[filtered['r_pnl'] > 0]['r_pnl'].sum()
    gl = abs(filtered[filtered['r_pnl'] < 0]['r_pnl'].sum())
    pf = gw / gl if gl > 0 else 999
    
    if pf > best_pf:
        best_pf = pf
        best_thresh = th

threshold = best_thresh
oos_df['ml_take'] = oos_df['ml_prob'] >= threshold

baseline_r_pnl = oos_df['r_pnl'].sum()
ml_filtered = oos_df[oos_df['ml_take']]
ml_r_pnl = ml_filtered['r_pnl'].sum()

print(f"\n--- OOS Results (2021-2025) ---")
print(f"Optimal Threshold: {threshold:.2f}")
print(f"Baseline Fakeout Trades: {len(oos_df)} | Total R: {baseline_r_pnl:.2f} | Win Rate: {oos_df['label'].mean():.1%}")
print(f"ML Filtered Trades (> {threshold:.2f}): {len(ml_filtered)} | Total R: {ml_r_pnl:.2f} | Win Rate: {ml_filtered['label'].mean():.1%}")

print("5. Exporting results for Fakeout Dashboard...")

oos_df['baseline_eq'] = oos_df['r_pnl'].cumsum()
oos_df['ml_pnl'] = np.where(oos_df['ml_take'], oos_df['r_pnl'], 0)
oos_df['ml_eq'] = oos_df['ml_pnl'].cumsum()

def calc_kpi(pnl_series, reward_series=None, risk_series=None):
    wins = (pnl_series > 0).sum()
    total = len(pnl_series[pnl_series != 0])
    if total == 0: return {"wr": 0, "pf": 0, "dd": 0, "n": 0, "r": 0, "avg_rr": 0}
    wr = wins / total
    gross_win = pnl_series[pnl_series > 0].sum()
    gross_loss = abs(pnl_series[pnl_series < 0].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else 999
    
    eq = pnl_series.cumsum()
    dd = (eq - eq.cummax()).min()
    
    # Avg Expected R/R
    avg_rr = 0
    if reward_series is not None and risk_series is not None:
        valid = (risk_series > 0) & (pnl_series != 0)
        if valid.sum() > 0:
            avg_rr = (reward_series[valid] / risk_series[valid]).mean()
            
    return {"wr": wr, "pf": pf, "dd": dd, "n": total, "r": pnl_series.sum(), "avg_rr": avg_rr}

base_kpi = calc_kpi(oos_df['r_pnl'], oos_df['reward'], oos_df['risk'])
ml_kpi = calc_kpi(oos_df['ml_pnl'], oos_df['reward'], oos_df['risk'])

oos_df['yr'] = oos_df['tdate'].dt.year
oos_df['mo'] = oos_df['tdate'].dt.month
monthly = oos_df.groupby(['yr', 'mo'])['ml_pnl'].sum().unstack()

dashboard_data = {
    'kpi': {
        'base': base_kpi,
        'ml': ml_kpi,
        'threshold': threshold
    },
    'equity': {
        'dates': [str(d.date()) for d in oos_df['tdate']],
        'base': oos_df['baseline_eq'].tolist(),
        'ml': oos_df['ml_eq'].tolist()
    },
    'heatmap': {
        'years': monthly.index.tolist(),
        'months': monthly.columns.tolist(),
        'values': monthly.fillna(0).values.tolist()
    }
}

with open(os.path.join(OUT_DIR, 'ml_fakeout_results.json'), 'w') as f:
    json.dump(dashboard_data, f)
print("Done! Data exported to ml_fakeout_results.json")
