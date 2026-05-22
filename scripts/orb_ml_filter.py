"""
ML Walk-Forward Filter for ORB VWAP Long Strategy (Vectorized Version)
======================================================================
- Long-only mode
- Feature engineering vectorized with Pandas groupby/shift (fast)
- Walk-Forward cross-validation (no future leakage)
- Output: ML-filtered vs baseline equity curves
"""

import pandas as pd
import numpy as np
import databento as db
import plotly.graph_objects as go
from datetime import time
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================
DATA_FILE   = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
RESULTS_CSV = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\vwap_retest_raw_results.csv"
OUT_HTML    = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\ml_equity_curve.html"
FEAT_HTML   = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\ml_feature_importance.html"

TP_SIZE         = 0.5
TRAIN_YEARS     = 3
PROB_THRESHOLD  = 0.52

# ============================================================
# STEP 1: Load 1m data (front-month NQ only)
# ============================================================
print("Loading 1m data...")
store = db.DBNStore.from_file(DATA_FILE)
df = store.to_df()
df = df[df['symbol'].astype(str).str.match(r'^NQ[HMUZ]\d$')]
df.index = pd.to_datetime(df.index).tz_convert('US/Eastern')
df['date'] = df.index.date

daily_vol    = df.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df = df.reset_index().merge(front_months, on=['date', 'symbol']).set_index('ts_event').sort_index()

df['date'] = df.index.date
df['time'] = df.index.time
df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3.0
print(f"Data ready: {len(df)} rows, {df['date'].nunique()} days")

# ============================================================
# STEP 2: Build daily feature table (vectorized)
# ============================================================
print("Building daily feature table (vectorized)...")

# --- RTH slice -----------------------------------------
rth = df[(df['time'] >= time(9, 30)) & (df['time'] <= time(16, 0))].copy()

# ORB slice (09:30 – 10:00)
orb = df[(df['time'] >= time(9, 30)) & (df['time'] < time(10, 0))].copy()
orb['pv'] = orb['hlc3'] * orb['volume']

daily_orb = orb.groupby('date').agg(
    orbH       = ('high',   'max'),
    orbL       = ('low',    'min'),
    orb_vol    = ('volume', 'sum'),
    orb_open   = ('open',   'first'),
    orb_pv     = ('pv',     'sum'),
).reset_index()
daily_orb['orb_range']     = daily_orb['orbH'] - daily_orb['orbL']
daily_orb['orb_range_pct'] = daily_orb['orb_range'] / daily_orb['orb_open'].replace(0, np.nan)
daily_orb['vwap_at_orb']   = daily_orb['orb_pv'] / daily_orb['orb_vol'].replace(0, np.nan)
daily_orb['vwap_distance'] = daily_orb['orbH'] - daily_orb['vwap_at_orb']
daily_orb['vwap_dist_pct'] = daily_orb['vwap_distance'] / daily_orb['orbH'].replace(0, np.nan)

# RTH daily open / close for return features
daily_rth = rth.groupby('date').agg(
    rth_open  = ('open',  'first'),
    rth_close = ('close', 'last'),
).reset_index()
daily_rth['day_return'] = (daily_rth['rth_close'] - daily_rth['rth_open']) / daily_rth['rth_open'].replace(0, np.nan)

# Merge
feat = daily_orb.merge(daily_rth, on='date', how='inner')
feat = feat.sort_values('date').reset_index(drop=True)

# Lagged features (shift to avoid future leakage)
feat['prev_day_return']   = feat['day_return'].shift(1)
feat['prev_5day_return']  = feat['rth_close'].pct_change(5).shift(1)
feat['open_gap']          = (feat['orb_open'] - feat['rth_close'].shift(1)) / feat['rth_close'].shift(1).replace(0, np.nan)
feat['orb_vol_10d_avg']   = feat['orb_vol'].shift(1).rolling(10, min_periods=5).mean()
feat['orb_vol_ratio']     = feat['orb_vol'] / feat['orb_vol_10d_avg'].replace(0, np.nan)
feat['date_str']          = feat['date'].astype(str)

print(f"Feature table ready: {len(feat)} rows")

# ============================================================
# STEP 3: Merge with Long trade results
# ============================================================
print("Loading backtest Long results...")
res = pd.read_csv(RESULTS_CSV)
res = res[(res['TP_Size'] == TP_SIZE) & (res['Direction'] == 'Long')].copy()
res['Date'] = pd.to_datetime(res['Date'])
res['date_str'] = res['Date'].dt.strftime('%Y-%m-%d')
res['Label'] = (res['PnL'] > 0).astype(int)

merged = feat.merge(res[['date_str', 'Label', 'PnL', 'Entry_Time', 'Exit_Reason']], on='date_str', how='inner')
merged = merged.sort_values('date').reset_index(drop=True)
merged['date'] = pd.to_datetime(merged['date'])

FEATURE_COLS = ['orb_range', 'orb_range_pct', 'vwap_distance', 'vwap_dist_pct',
                'open_gap', 'prev_day_return', 'prev_5day_return', 'orb_vol_ratio']

merged = merged.dropna(subset=FEATURE_COLS)
print(f"Merged dataset: {len(merged)} rows | Baseline win-rate: {merged['Label'].mean():.1%}")

# ============================================================
# STEP 4: Walk-Forward Validation
# ============================================================
print(f"\n=== Walk-Forward (Train={TRAIN_YEARS}yr, P_threshold={PROB_THRESHOLD}) ===")

merged['year'] = merged['date'].dt.year
years = sorted(merged['year'].unique())

wf_results = []
feat_importances = []

for test_year in years[TRAIN_YEARS:]:
    train_years = [y for y in years if y < test_year][-TRAIN_YEARS:]
    train = merged[merged['year'].isin(train_years)]
    test  = merged[merged['year'] == test_year].copy()

    if len(train) < 50 or len(test) < 5:
        continue

    X_tr = train[FEATURE_COLS].values
    y_tr = train['Label'].values
    X_te = test[FEATURE_COLS].values
    y_te = test['Label'].values

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    rf = RandomForestClassifier(
        n_estimators=300, max_depth=4,
        min_samples_leaf=12, class_weight='balanced', 
        random_state=42, n_jobs=-1
    )
    rf.fit(X_tr_s, y_tr)
    proba = rf.predict_proba(X_te_s)[:, 1]

    test = test.copy()
    test['ML_Prob']  = proba
    test['ML_Enter'] = (proba >= PROB_THRESHOLD).astype(int)
    wf_results.append(test)
    feat_importances.append(dict(zip(FEATURE_COLS, rf.feature_importances_)))

    ml_mask = test['ML_Enter'] == 1
    n_total = len(test)
    n_enter = ml_mask.sum()
    bl_wr   = y_te.mean()
    bl_pnl  = test['PnL'].sum()
    ml_wr   = test.loc[ml_mask, 'Label'].mean() if n_enter > 0 else np.nan
    ml_pnl  = test.loc[ml_mask, 'PnL'].sum()
    print(f"  [{test_year}] ALL {n_total} trades: {bl_wr:.1%}wr {bl_pnl:+.0f}pts | "
          f"ML selects {n_enter}/{n_total}: {ml_wr:.1%}wr {ml_pnl:+.0f}pts")

# ============================================================
# STEP 5: Aggregate and Plot
# ============================================================
if not wf_results:
    print("Not enough data for Walk-Forward validation.")
    exit(0)

all_wf = pd.concat(wf_results).sort_values('date')
all_wf['Cum_PnL_all'] = all_wf['PnL'].cumsum()
ml = all_wf[all_wf['ML_Enter'] == 1].copy()
ml['Cum_PnL_ml'] = ml['PnL'].cumsum()

bl_wr  = all_wf['Label'].mean()
ml_wr  = ml['Label'].mean() if len(ml) > 0 else 0
bl_pnl = all_wf['PnL'].sum()
ml_pnl = ml['PnL'].sum()

print(f"\n=== FINAL WALK-FORWARD SUMMARY ===")
print(f"Baseline (All Longs): {len(all_wf)} trades | {bl_wr:.1%} win-rate | {bl_pnl:+.0f} pts")
print(f"ML Filter (P>{PROB_THRESHOLD}): {len(ml)} trades | {ml_wr:.1%} win-rate | {ml_pnl:+.0f} pts")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=all_wf['date'], y=all_wf['Cum_PnL_all'], mode='lines',
    name=f'📋 All Longs ({len(all_wf)} trades | {bl_wr:.1%} WR | {bl_pnl:+.0f}pts)',
    line=dict(color='#78909c', width=2, dash='dot')
))
fig.add_trace(go.Scatter(
    x=ml['date'], y=ml['Cum_PnL_ml'], mode='lines',
    name=f'🤖 ML Filtered ({len(ml)} trades | {ml_wr:.1%} WR | {ml_pnl:+.0f}pts)',
    line=dict(color='#00e5ff', width=3)
))
fig.update_layout(
    title=(f"ML Walk-Forward Filter vs Baseline  (TP={TP_SIZE}x, Long-Only, P>{PROB_THRESHOLD})<br>"
           f"Baseline: {bl_pnl:+.0f}pts → ML Filtered: {ml_pnl:+.0f}pts"),
    xaxis_title="Date", yaxis_title="Cumulative PnL (NQ Points)",
    template="plotly_dark", hovermode='x unified', height=550,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
)
fig.write_html(OUT_HTML)
print(f"Equity curve → {OUT_HTML}")

# Feature Importance
if feat_importances:
    avg_imp = pd.DataFrame(feat_importances).mean().sort_values(ascending=True)
    fig2 = go.Figure(go.Bar(
        x=avg_imp.values, y=avg_imp.index,
        orientation='h', marker_color='#00e5ff',
        text=[f"{v:.3f}" for v in avg_imp.values], textposition='outside'
    ))
    fig2.update_layout(
        title="RF Feature Importance (avg across Walk-Forward folds)",
        xaxis_title="Importance", template="plotly_dark", height=400
    )
    fig2.write_html(FEAT_HTML)
    print(f"Feature importance → {FEAT_HTML}")
