"""
ORB + VWAP Retest — Integrated Markov Regime & ML Dynamic TP
============================================================
核心邏輯：
  1. 使用 HMM (Walk-Forward) 識別每日波動環境 (Regime)。
  2. 使用 XGBoost (Walk-Forward) 預測交易進場後的最大利潤 (MFE)。
  3. 組合過濾：
     - 環境過濾：只在 Med Vol 環境下進場（回測顯示 Med Vol 最具趨勢性）。
     - 出場動態：TP = Predicted_MFE × Scale (暫定 0.7)。
  4. 輸出：對比 Baseline, ML, ML+Regime 績效。

Dependencies: databento, pandas, numpy, plotly, hmmlearn, xgboost, scikit-learn
"""

import databento as db
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
import os
import warnings
from datetime import time
from hmmlearn.hmm import GaussianHMM
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\integrated_strategy"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Strategy Core
ORB_MIN              = 30
SESSION_ENTRY_CUTOFF = time(12, 0)
SESSION_FORCE_EXIT   = time(15, 55)

# ML/HMM Walk-Forward
HMM_LOOKBACK_DAYS = 504
WF_TRAIN_YEARS    = 3
SCALE_FACTOR      = 0.70  # TP = MFE_pred × 0.7

pio.templates.default = "plotly_dark"

# =============================================================================
# PHASE 1: DATA LOADING & PREPROCESSING
# =============================================================================
print("=" * 60)
print("PHASE 1: Loading data...")

store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

df_1m = df_1m[df_1m['symbol'].astype(str).str.match(r'^NQ[HMUZ]\d$')].copy()
df_1m['date'] = df_1m.index.date
df_1m['time'] = df_1m.index.time

# Front-month routing
daily_vol = df_1m.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df_1m = df_1m.reset_index().merge(front_months, on=['date', 'symbol'], how='inner')
df_1m.set_index('ts_event', inplace=True)
df_1m.sort_index(inplace=True)

# HLC3, VWAP, TR
df_1m['hlc3'] = (df_1m['high'] + df_1m['low'] + df_1m['close']) / 3.0
rth_mask = df_1m.index.time >= time(9, 30)
df_1m.loc[rth_mask, 'pVol'] = df_1m[rth_mask]['hlc3'] * df_1m[rth_mask]['volume']
df_1m['vwap'] = np.nan
grouped_rth = df_1m[rth_mask].groupby('date')
rth_vwap_val = grouped_rth['pVol'].cumsum() / (grouped_rth['volume'].cumsum() + 1e-9)
df_1m.loc[rth_mask, 'vwap'] = rth_vwap_val
df_1m['vwap'] = df_1m.groupby('date')['vwap'].ffill().ffill()

df_1m['prev_close_1m'] = df_1m.groupby('date')['close'].shift(1)
df_1m['tr'] = np.maximum(
    df_1m['high'] - df_1m['low'],
    np.maximum(
        (df_1m['high'] - df_1m['prev_close_1m']).abs(),
        (df_1m['low']  - df_1m['prev_close_1m']).abs(),
    )
).fillna(0)

# =============================================================================
# PHASE 2: DAILY REGIME DETECTION (WALK-FORWARD)
# =============================================================================
print("\nPHASE 2: HMM Regime Detection (Walk-Forward)...")

daily_ohlc = df_1m[df_1m.index.time >= time(9, 30)].groupby('date').agg(
    daily_open=('open', 'first'), daily_high=('high', 'max'),
    daily_low=('low', 'min'), daily_close=('close', 'last'),
    daily_volume=('volume', 'sum'),
).reset_index()
daily_ohlc['date'] = pd.to_datetime(daily_ohlc['date'])
daily_ohlc['log_return'] = np.log(daily_ohlc['daily_close'] / daily_ohlc['daily_close'].shift(1))
daily_ohlc['range_pct']  = (daily_ohlc['daily_high'] - daily_ohlc['daily_low']) / (daily_ohlc['daily_close'] + 1e-9)
daily_ohlc['parkinson_vol'] = np.sqrt((1 / (4 * np.log(2))) * (np.log(daily_ohlc['daily_high'] / (daily_ohlc['daily_low'] + 1e-9))) ** 2)
daily_ohlc['vol_5d'] = daily_ohlc['parkinson_vol'].rolling(5).mean()
daily_ohlc.dropna(subset=['log_return', 'range_pct', 'vol_5d'], inplace=True)
daily_ohlc.reset_index(drop=True, inplace=True)

obs_cols = ['log_return', 'range_pct', 'vol_5d']
daily_ohlc['hmm_regime'] = np.nan
daily_ohlc['year'] = daily_ohlc['date'].dt.year
years = sorted(daily_ohlc['year'].unique())

for yr in years:
    yr_mask = daily_ohlc['year'] == yr
    yr_idx = daily_ohlc[yr_mask].index
    if len(yr_idx) == 0: continue
    
    train_end = yr_idx[0]
    train_start = max(0, train_end - HMM_LOOKBACK_DAYS)
    if train_end - train_start < 100: continue
    
    X_train = daily_ohlc.loc[train_start:train_end-1, obs_cols].values
    X_test = daily_ohlc.loc[yr_idx, obs_cols].values
    
    try:
        # Use 'diag' for better stability on Windows/Gemini environment
        hmm = GaussianHMM(n_components=3, covariance_type='diag', n_iter=100, random_state=42)
        hmm.fit(X_train)
        regimes_tr = hmm.predict(X_train)
        regimes_te = hmm.predict(X_test)
        
        # Sort by avg abs log return (0=Low, 1=Med, 2=High vol)
        tr_stats = pd.DataFrame({'r': regimes_tr, 'ret': np.abs(X_train[:, 0])}).groupby('r')['ret'].mean().sort_values()
        map_dict = {orig: rank for rank, orig in enumerate(tr_stats.index)}
        daily_ohlc.loc[yr_idx, 'hmm_regime'] = [map_dict[r] for r in regimes_te]
    except:
        continue

# SHIFT: Avoid look-ahead (Today's trading uses yesterday's regime)
daily_ohlc['regime_for_trading'] = daily_ohlc['hmm_regime'].shift(1)
regime_lookup = dict(zip(daily_ohlc['date'].dt.date, daily_ohlc['regime_for_trading']))
daily_info_lookup = daily_ohlc.set_index('date').to_dict('index')

# =============================================================================
# PHASE 3: ORB BACKTEST + FEATURE EXTRACTION (MFE)
# =============================================================================
print("\nPHASE 3: ORB Backtest + Feature extraction...")

dates = sorted(df_1m['date'].unique())
all_trades = []

for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    try: day_data = df_1m.loc[day_str]
    except KeyError: continue
    if day_data.empty: continue
    
    regime_val = regime_lookup.get(trade_date, np.nan)
    prev_info = daily_info_lookup.get(trade_date, {})
    atr_14 = prev_info.get('vol_5d', np.nan) * 100 # scaling

    orb_end_dt = pd.Timestamp(f"{day_str} 09:30:00", tz='US/Eastern') + pd.Timedelta(minutes=ORB_MIN)
    orb_end_time = orb_end_dt.time()
    
    orb_bars = day_data[(day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)]
    if len(orb_bars) < 5: continue
    
    orbH, orbL = orb_bars['high'].max(), orb_bars['low'].min()
    orbRange = orbH - orbL
    if orbRange <= 0: continue
    
    # ORB ATR
    intraday_atr = orb_bars['tr'].mean()
    orb_momentum = (orb_bars['close'].iloc[-1] - orb_bars['open'].iloc[0]) / (orb_bars['open'].iloc[0] + 1e-9)

    # Entry Logic
    entry_window = day_data[(day_data['time'] >= orb_end_time) & (day_data['time'] <= SESSION_ENTRY_CUTOFF)]
    has_traded, p_long, p_short = False, False, False
    entry_price, e_time, e_dir, sl_px = 0, None, None, 0
    
    for idx, row in entry_window.iterrows():
        if has_traded: break
        w_l, w_s = p_long, p_short
        if not p_long and not p_short:
            if idx.minute % 5 == 4:
                if row['close'] > orbH: p_long = True
                if row['close'] < orbL: p_short = True
        
        vwap = row['vwap']
        if w_l:
            sl_px = orbL
            if vwap > sl_px and row['low'] <= vwap:
                entry_price, e_time, e_dir, has_traded = vwap, idx, 'Long', True
        elif w_s:
            sl_px = orbH
            if vwap < sl_px and row['high'] >= vwap:
                entry_price, e_time, e_dir, has_traded = vwap, idx, 'Short', True
    
    if not has_traded: continue
    
    # MFE Calculation
    ex_idx = day_data.index.get_loc(e_time) + 1
    ex_path = day_data.iloc[ex_idx:]
    if ex_path.empty: continue
    
    time_mask = ex_path['time'] < SESSION_FORCE_EXIT
    p_in_t = ex_path[time_mask]
    if p_in_t.empty: continue
    
    sl_dist = abs(entry_price - sl_px)
    if e_dir == 'Long':
        f_exc = p_in_t['high'] - entry_price
        a_exc = entry_price - p_in_t['low']
    else:
        f_exc = entry_price - p_in_t['low']
        a_exc = p_in_t['high'] - entry_price

    sl_hit_mask = a_exc >= sl_dist
    if sl_hit_mask.any():
        f_before_sl = f_exc[:sl_hit_mask.idxmax()]
        mfe_val = f_before_sl.max() if not f_before_sl.empty else 0
        res = 'SL'
    else:
        mfe_val = f_exc.max()
        res = 'Survived'
    
    all_trades.append({
        'date': trade_date, 'regime': regime_val, 'dir': e_dir, 'entry_px': entry_price, 
        'sl_dist': sl_dist, 'mfe': max(mfe_val, 0), 'res': res, 'orbRange': orbRange,
        'intraday_atr': intraday_atr, 'orb_momentum': orb_momentum, 'year': trade_date.year
    })

trades_df = pd.DataFrame(all_trades).dropna(subset=['regime'])

# =============================================================================
# PHASE 4: ML MFE PREDICTION (WALK-FORWARD)
# =============================================================================
print("\nPHASE 4: ML MFE Prediction (Walk-Forward)...")

FEATURES = ['regime', 'intraday_atr', 'orbRange', 'orb_momentum', 'sl_dist']
trades_df['mfe_pred'] = np.nan
years_wf = sorted(trades_df['year'].unique())

for yr in years_wf:
    test_m = trades_df['year'] == yr
    train_m = (trades_df['year'] >= yr - WF_TRAIN_YEARS) & (trades_df['year'] < yr)
    if train_m.sum() < 50 or test_m.sum() < 5: continue
    
    X_tr, y_tr = trades_df.loc[train_m, FEATURES], trades_df.loc[train_m, 'mfe']
    X_te = trades_df.loc[test_m, FEATURES]
    
    model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    model.fit(X_tr, y_tr)
    trades_df.loc[test_m, 'mfe_pred'] = np.clip(model.predict(X_te), 0, None)

oos_trades = trades_df.dropna(subset=['mfe_pred']).copy()

# =============================================================================
# PHASE 5: COMBINED STRATEGY SIMULATION
# =============================================================================
print("\nPHASE 5: Simulating Strategies...")

configs = [
    {'name': 'Baseline (1R)', 'reg_filt': None, 'tp': 'fixed', 'mult': 1.0},
    {'name': 'ML Dynamic TP', 'reg_filt': None, 'tp': 'ml', 'mult': SCALE_FACTOR},
    {'name': 'ML + Med Vol Filter', 'reg_filt': 1, 'tp': 'ml', 'mult': SCALE_FACTOR},
    {'name': 'ML + Excl High Vol', 'reg_filt': [0, 1], 'tp': 'ml', 'mult': SCALE_FACTOR},
]

results = []
eq_curves = {}

for cfg in configs:
    # Filter by regime
    f_df = oos_trades.copy()
    if cfg['reg_filt'] is not None:
        regs = cfg['reg_filt'] if isinstance(cfg['reg_filt'], list) else [cfg['reg_filt']]
        f_df = f_df[f_df['regime'].isin(regs)]
    
    if f_df.empty: continue
    
    pnl_list = []
    for _, r in f_df.iterrows():
        tp_pts = (r['orbRange'] * cfg['mult']) if cfg['tp'] == 'fixed' else (r['mfe_pred'] * cfg['mult'])
        if tp_pts <= r['mfe']: pnl = tp_pts
        elif r['res'] == 'SL': pnl = -r['sl_dist']
        else: pnl = 0
        pnl_list.append(pnl)
    
    pnl_s = pd.Series(pnl_list)
    wins = (pnl_s > 0).sum()
    wr = wins / len(pnl_s)
    total = pnl_s.sum()
    sharpe = (pnl_s.mean() / (pnl_s.std() + 1e-9)) * np.sqrt(252)
    
    results.append({'Strategy': cfg['name'], 'Trades': len(f_df), 'WinRate': wr, 'TotalPnL': total, 'Sharpe': sharpe})
    
    f_df['pnl'] = pnl_list
    eq_curves[cfg['name']] = f_df.sort_values('date')[['date', 'pnl']]

res_df = pd.DataFrame(results)
print("\n=== PERFORMANCE RESULTS ===")
print(res_df.to_string(index=False))

# =============================================================================
# PHASE 6: DASHBOARD GENERATION
# =============================================================================
fig_eq = go.Figure()
for name, eq in eq_curves.items():
    fig_eq.add_trace(go.Scatter(x=eq['date'], y=eq['pnl'].cumsum(), name=name))
fig_eq.update_layout(title="Integrated Strategy Equity Curves", xaxis_title="Date", yaxis_title="Cumulative PnL")

res_df['WinRatePct'] = res_df['WinRate'] * 100
fig_bar = make_subplots(rows=1, cols=3, subplot_titles=("Win Rate %", "Total PnL", "Sharpe Ratio"))
fig_bar.add_trace(go.Bar(x=res_df['Strategy'], y=res_df['WinRatePct'], marker_color='blue'), row=1, col=1)
fig_bar.add_trace(go.Bar(x=res_df['Strategy'], y=res_df['TotalPnL'], marker_color='green'), row=1, col=2)
fig_bar.add_trace(go.Bar(x=res_df['Strategy'], y=res_df['Sharpe'], marker_color='gold'), row=1, col=3)
fig_bar.update_layout(height=400, showlegend=False, title_text="Strategy Comparison")

html = f"<html><head><title>Integrated ORB Strategy</title></head><body style='background:#111;color:#eee;font-family:sans-serif;padding:40px;'>"
html += "<h1>Integrated Markov Regime + ML Dynamic TP</h1>"
html += "<p>Only trading in identified Med Vol (Regime 1) environments using Predicted MFE as dynamic TP.</p>"
html += fig_eq.to_html(full_html=False, include_plotlyjs='cdn')
html += fig_bar.to_html(full_html=False, include_plotlyjs='cdn')
html += "<h2>Performance Summary Table</h2>"
html += res_df.to_html()
html += "</body></html>"

out_path = os.path.join(OUTPUT_DIR, "integrated_dashboard.html")
with open(out_path, "w", encoding="utf-8") as f: f.write(html)
print(f"\nDashboard saved to: {out_path}")
