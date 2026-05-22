"""
ORB + VWAP Retest — ML Dynamic TP (High Win Rate)
==================================================
目標：高勝率 + 小但穩定盈虧比

核心創新：
  1. 計算每筆交易的 MFE（Maximum Favorable Excursion）= 進場後最大有利浮盈
  2. 提取開盤 ATR（09:30 到 ORB 結束的 1m True Range 均值）作為核心特徵
  3. 訓練 XGBoost Regressor 預測每筆交易的 MFE
  4. 動態 TP = Predicted_MFE × scale_factor (0.65~0.85)
  5. 對比固定 TP vs ML 動態 TP 的績效

Walk-Forward: 訓練過去資料，預測當年，避免未來資料洩漏
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
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score

warnings.filterwarnings('ignore')

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\ml_dynamic_tp"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Strategy Core
ORB_MIN              = 30
SESSION_ENTRY_CUTOFF = time(12, 0)
SESSION_FORCE_EXIT   = time(15, 55)

# ML Walk-Forward
WF_TRAIN_YEARS = 3
SCALE_FACTORS  = [0.65, 0.70, 0.75, 0.80, 0.85]  # TP = MFE_pred × scale

# Reference fixed TPs for comparison (in ORB range multiples)
FIXED_TP_SIZES = [0.5, 0.8, 1.0, 1.5]

pio.templates.default = "plotly_dark"

# =============================================================================
# --- PHASE 1: DATA LOADING ---
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

daily_vol   = df_1m.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df_1m = df_1m.reset_index().merge(front_months, on=['date', 'symbol'], how='inner')
df_1m.set_index('ts_event', inplace=True)
df_1m.sort_index(inplace=True)

print(f"  Rows: {len(df_1m):,}")

# HLC3 + VWAP
df_1m['hlc3'] = (df_1m['high'] + df_1m['low'] + df_1m['close']) / 3.0
rth_mask = df_1m.index.time >= time(9, 30)
df_1m.loc[rth_mask, 'pVol'] = df_1m[rth_mask]['hlc3'] * df_1m[rth_mask]['volume']
df_1m['vwap'] = np.nan
grouped_rth = df_1m[rth_mask].groupby('date')
rth_vwap_val = grouped_rth['pVol'].cumsum() / grouped_rth['volume'].cumsum()
df_1m.loc[rth_mask, 'vwap'] = rth_vwap_val
df_1m['vwap'] = df_1m.groupby('date')['vwap'].ffill().ffill()

# True Range per 1m bar (for intraday ATR)
df_1m['prev_close_1m'] = df_1m.groupby('date')['close'].shift(1)
df_1m['tr'] = np.maximum(
    df_1m['high'] - df_1m['low'],
    np.maximum(
        (df_1m['high'] - df_1m['prev_close_1m']).abs(),
        (df_1m['low']  - df_1m['prev_close_1m']).abs(),
    )
)

# Previous day OHLC for features
rth_data = df_1m[df_1m.index.time >= time(9, 30)]
daily_ohlc = rth_data.groupby('date').agg(
    daily_high=('high', 'max'), daily_low=('low', 'min'),
    daily_close=('close', 'last'), daily_open=('open', 'first'),
    daily_volume=('volume', 'sum'),
).reset_index()
daily_ohlc['prev_high']   = daily_ohlc['daily_high'].shift(1)
daily_ohlc['prev_low']    = daily_ohlc['daily_low'].shift(1)
daily_ohlc['prev_close']  = daily_ohlc['daily_close'].shift(1)
daily_ohlc['tr14'] = (daily_ohlc['daily_high'] - daily_ohlc['daily_low'])
daily_ohlc['atr_14'] = daily_ohlc['tr14'].rolling(14, min_periods=3).mean()
daily_info_lookup = daily_ohlc.set_index('date').to_dict('index')

dates = sorted(df_1m['date'].unique())
print(f"  Trading days: {len(dates)}")

# =============================================================================
# --- PHASE 2: BACKTEST + FEATURE EXTRACTION + MFE RECORDING ---
# =============================================================================
print("\nPHASE 2: Backtest + Feature extraction + MFE recording...")

all_records = []  # One record per traded day (MFE + features)

for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    try:
        day_data = df_1m.loc[day_str]
    except KeyError:
        continue
    if day_data.empty:
        continue

    prev_info  = daily_info_lookup.get(trade_date, {})
    prev_close = prev_info.get('prev_close',  np.nan)
    prev_high  = prev_info.get('prev_high',   np.nan)
    prev_low   = prev_info.get('prev_low',    np.nan)
    atr_14     = prev_info.get('atr_14',      np.nan)
    today_open = prev_info.get('daily_open',  np.nan)

    orb_end_dt   = pd.Timestamp(f"{day_str} 09:30:00", tz='US/Eastern') + pd.Timedelta(minutes=ORB_MIN)
    orb_end_time = orb_end_dt.time()

    # ORB bars
    orb_mask = (day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)
    orb_bars = day_data[orb_mask]
    if orb_bars.empty or len(orb_bars) < 5:
        continue

    orbH     = orb_bars['high'].max()
    orbL     = orb_bars['low'].min()
    orbRange = orbH - orbL
    if orbRange <= 0:
        continue

    # === Intraday ATR features ===
    orb_trs          = orb_bars['tr'].dropna()
    intraday_atr     = orb_trs.mean() if len(orb_trs) > 0 else np.nan
    intraday_atr_std = orb_trs.std()  if len(orb_trs) > 1 else 0
    # Trend of ATR within ORB: expanding or contracting?
    first_half  = orb_trs.iloc[:len(orb_trs)//2].mean()  if len(orb_trs) > 2 else np.nan
    second_half = orb_trs.iloc[len(orb_trs)//2:].mean()  if len(orb_trs) > 2 else np.nan
    atr_trend   = (second_half - first_half) / (first_half + 1e-9)  # positive = expanding

    # ORB structure features
    orb_close      = orb_bars['close'].iloc[-1]
    orb_open_val   = orb_bars['open'].iloc[0]
    orb_momentum   = (orb_close - orb_open_val) / orb_open_val if orb_open_val > 0 else 0
    orb_body_ratio = abs(orb_close - orb_open_val) / (orbRange + 1e-9)
    orb_vol        = orb_bars['volume'].sum()
    gap_pct        = (today_open - prev_close) / prev_close if prev_close > 0 else 0
    orb_range_vs_atr14 = orbRange / atr_14 if atr_14 > 0 else np.nan
    orb_range_vs_intra = orbRange / intraday_atr if intraday_atr and intraday_atr > 0 else np.nan
    vwap_at_orb    = orb_bars['vwap'].iloc[-1]
    orb_mid        = (orbH + orbL) / 2
    vwap_vs_mid    = (vwap_at_orb - orb_mid) / orbRange

    # === Entry scan ===
    entry_window = day_data[
        (day_data['time'] >= orb_end_time) &
        (day_data['time'] <= SESSION_ENTRY_CUTOFF)
    ]
    if entry_window.empty:
        continue

    has_traded    = False
    pending_long  = False
    pending_short = False
    entry_price   = 0.0
    entry_time    = None
    entry_dir     = None
    sl_price      = 0.0

    for idx, row in entry_window.iterrows():
        if has_traded:
            break
        was_pl, was_ps = pending_long, pending_short

        if not pending_long and not pending_short:
            if idx.minute % 5 == 4:
                if row['close'] > orbH:
                    pending_long = True
                if row['close'] < orbL:
                    pending_short = True

        vwap_val = row['vwap']
        if was_pl:
            sl_price = orbL
            if vwap_val > sl_price and row['low'] <= vwap_val:
                entry_price = vwap_val if vwap_val <= row['high'] else row['high']
                entry_time  = idx
                entry_dir   = 'Long'
                has_traded  = True
        elif was_ps:
            sl_price = orbH
            if vwap_val < sl_price and row['high'] >= vwap_val:
                entry_price = vwap_val if vwap_val >= row['low'] else row['low']
                entry_time  = idx
                entry_dir   = 'Short'
                has_traded  = True

    if not has_traded:
        continue

    # === Compute MFE + MAE for exit path ===
    try:
        exit_idx_pos = day_data.index.get_loc(entry_time) + 1
        exit_path = day_data.iloc[exit_idx_pos:] if exit_idx_pos < len(day_data) else pd.DataFrame()
    except Exception:
        exit_path = pd.DataFrame()

    if exit_path.empty:
        continue

    # SL hit position from entry
    sl_dist = abs(entry_price - sl_price)

    if entry_dir == 'Long':
        excursion_series = exit_path['high'] - entry_price   # favorable
        adverse_series   = entry_price - exit_path['low']    # adverse
    else:
        excursion_series = entry_price - exit_path['low']    # favorable
        adverse_series   = exit_path['high'] - entry_price   # adverse

    # Restrict to before force exit
    time_mask   = exit_path['time'] < SESSION_FORCE_EXIT
    exc_in_time = excursion_series[time_mask]
    adv_in_time = adverse_series[time_mask]

    # Find MFE: max favorable before SL is hit
    sl_hit_idx = (adv_in_time >= sl_dist).idxmax() if (adv_in_time >= sl_dist).any() else None

    if sl_hit_idx is not None:
        exc_before_sl = exc_in_time.loc[:sl_hit_idx]
        mfe = exc_before_sl.max() if not exc_before_sl.empty else 0.0
        trade_result = 'SL'
    else:
        mfe = exc_in_time.max() if not exc_in_time.empty else 0.0
        trade_result = 'Survived'

    mfe = max(mfe, 0.0)

    # VWAP at entry time (for post-entry features)
    vwap_at_entry = entry_window.loc[entry_time, 'vwap'] if entry_time in entry_window.index else np.nan

    all_records.append({
        'date'              : trade_date,
        'direction'         : entry_dir,
        'entry_price'       : entry_price,
        'sl_price'          : sl_price,
        'sl_dist'           : sl_dist,
        'orbH'              : orbH,
        'orbL'              : orbL,
        'orbRange'          : orbRange,
        'mfe'               : mfe,
        'trade_result'      : trade_result,
        # Features
        'intraday_atr'      : intraday_atr,
        'intraday_atr_std'  : intraday_atr_std,
        'atr_trend'         : atr_trend,
        'orb_range_vs_atr14': orb_range_vs_atr14,
        'orb_range_vs_intra': orb_range_vs_intra,
        'orb_momentum'      : orb_momentum,
        'orb_body_ratio'    : orb_body_ratio,
        'gap_pct'           : gap_pct,
        'vwap_vs_mid'       : vwap_vs_mid,
        'orb_vol'           : orb_vol,
        'prev_high'         : prev_high,
        'prev_low'          : prev_low,
        'day_of_week'       : trade_date.weekday(),
    })

records_df = pd.DataFrame(all_records)
records_df['date'] = pd.to_datetime(records_df['date'])
records_df['year'] = records_df['date'].dt.year

print(f"  Total traded days recorded: {len(records_df)}")
print(f"  MFE median: {records_df['mfe'].median():.2f} pts")
print(f"  MFE mean:   {records_df['mfe'].mean():.2f} pts")
print(f"  MFE p25 / p75: {records_df['mfe'].quantile(0.25):.1f} / {records_df['mfe'].quantile(0.75):.1f} pts")

# =============================================================================
# --- PHASE 3: WALK-FORWARD MFE REGRESSION ---
# =============================================================================
print("\nPHASE 3: Walk-Forward MFE regression (XGBoost)...")

FEATURE_COLS = [
    'intraday_atr', 'intraday_atr_std', 'atr_trend',
    'orb_range_vs_atr14', 'orb_range_vs_intra',
    'orbRange', 'orb_momentum', 'orb_body_ratio',
    'gap_pct', 'vwap_vs_mid', 'day_of_week',
]

records_df['mfe_pred']  = np.nan
records_df['wf_fold']   = np.nan
fi_fold_list = []

years_all = sorted(records_df['year'].unique())
year_start = years_all[0]

for test_yr in range(year_start + WF_TRAIN_YEARS, years_all[-1] + 1):
    train_start = test_yr - WF_TRAIN_YEARS
    train_mask  = (records_df['year'] >= train_start) & (records_df['year'] <= test_yr - 1)
    test_mask   = records_df['year'] == test_yr

    X_train = records_df.loc[train_mask, FEATURE_COLS]
    y_train = records_df.loc[train_mask, 'mfe']
    X_test  = records_df.loc[test_mask, FEATURE_COLS]

    if len(X_train) < 30 or len(X_test) < 5:
        continue

    # Impute with training medians
    medians = X_train.median()
    X_tr_f  = X_train.fillna(medians)
    X_te_f  = X_test.fillna(medians)

    model = XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        verbosity=0,
        random_state=42,
    )
    model.fit(X_tr_f, y_train)

    preds = model.predict(X_te_f)
    preds = np.clip(preds, 0, None)   # MFE cannot be negative

    records_df.loc[test_mask, 'mfe_pred'] = preds
    fold_num = test_yr - (year_start + WF_TRAIN_YEARS)
    records_df.loc[test_mask, 'wf_fold']  = fold_num

    y_test = records_df.loc[test_mask, 'mfe']
    mae = mean_absolute_error(y_test, preds)
    r2  = r2_score(y_test, preds)

    fi = pd.DataFrame({'feature': FEATURE_COLS,
                       'importance': model.feature_importances_,
                       'fold': fold_num, 'test_year': test_yr})
    fi_fold_list.append(fi)

    print(f"  {test_yr}: train {train_start}-{test_yr-1} | "
          f"n_test={len(X_test)} | MAE={mae:.2f}pts | R2={r2:.3f} | "
          f"pred_mean={preds.mean():.1f} actual_mean={y_test.mean():.1f}")

print(f"\n  Walk-forward complete.")
fi_all = pd.concat(fi_fold_list)
fi_avg = fi_all.groupby('feature')['importance'].mean().sort_values(ascending=False).reset_index()
print("\n  Feature Importance (avg across folds):")
for _, r in fi_avg.iterrows():
    print(f"    {r['feature']:30s}: {r['importance']:.4f}")

# =============================================================================
# --- PHASE 4: SIMULATE TRADES WITH DYNAMIC TP ---
# =============================================================================
print("\nPHASE 4: Simulating trades with ML Dynamic TP...")

oos_df = records_df.dropna(subset=['mfe_pred']).copy()
print(f"  OOS validated trades: {len(oos_df)}")

def simulate_dynamic_tp(records, scale):
    """
    For each trade, set TP = mfe_pred × scale.
    Then replay the original exit path to determine actual outcome.
    Returns trade results.
    """
    rows = []
    for _, rec in records.iterrows():
        tp_pts = rec['mfe_pred'] * scale
        if tp_pts <= 0:
            continue

        day_str  = rec['date'].strftime('%Y-%m-%d')
        entry_px = rec['entry_price']
        sl_px    = rec['sl_price']
        sl_dist  = rec['sl_dist']
        entry_dir = rec['direction']

        if entry_dir == 'Long':
            tp_price = entry_px + tp_pts
        else:
            tp_price = entry_px - tp_pts

        # We need to re-scan exit path: store entry index by date + price
        # Use pre-computed MFE: if tp_pts <= mfe, TP was hit (win)
        #                       else trade ran its full course (SL or EOD)
        if tp_pts <= rec['mfe']:
            # TP was reached before SL → Win
            pnl       = tp_pts
            exit_reason = 'TP'
        else:
            # TP not reached → result is SL or near-zero (EOD close)
            # Conservative: assume SL hit if trade_result == 'SL'
            if rec['trade_result'] == 'SL':
                pnl = -sl_dist
                exit_reason = 'SL'
            else:
                # EOD: use mfe as proxy for close pnl (conservative: 0)
                pnl = 0.0
                exit_reason = 'EOD'

        rows.append({
            'date'       : rec['date'],
            'direction'  : entry_dir,
            'pnl'        : pnl,
            'exit_reason': exit_reason,
            'tp_pts'     : tp_pts,
            'mfe'        : rec['mfe'],
            'mfe_pred'   : rec['mfe_pred'],
            'scale'      : scale,
        })
    return pd.DataFrame(rows)

def calc_stats(pnl_s, label=''):
    n = len(pnl_s)
    if n == 0:
        return {'label': label, 'n': 0, 'wr': 0, 'total': 0,
                'avg': 0, 'sharpe': 0, 'maxdd': 0, 'pf': 0}
    wr  = (pnl_s > 0).mean()
    tot = pnl_s.sum()
    avg = pnl_s.mean()
    std = pnl_s.std() if n > 1 else 1e-9
    sh  = (avg / std) * np.sqrt(252) if std > 0 else 0
    cum = pnl_s.cumsum()
    mdd = (cum - cum.cummax()).min()
    gp  = pnl_s[pnl_s > 0].sum()
    gl  = pnl_s[pnl_s < 0].abs().sum()
    pf  = gp / gl if gl > 0 else np.inf
    return {'label': label, 'n': n, 'wr': wr, 'total': tot,
            'avg': avg, 'sharpe': sh, 'maxdd': mdd, 'pf': pf}

compare_rows = []
equity_curves = {}

# --- Dynamic TP results ---
for scale in SCALE_FACTORS:
    sim_df = simulate_dynamic_tp(oos_df, scale)
    pnl_s  = sim_df['pnl'].reset_index(drop=True)
    s = calc_stats(pnl_s, f'ML TP x{scale}')
    s['type']  = 'ML_Dynamic'
    s['scale'] = scale
    compare_rows.append(s)
    eq = sim_df[['date', 'pnl']].sort_values('date').copy()
    eq['cum_pnl'] = eq['pnl'].cumsum().values
    equity_curves[f'ML x{scale}'] = eq
    print(f"  ML TP x{scale:.2f}: n={int(len(sim_df))} WR={pnl_s[pnl_s>0].mean() if (pnl_s>0).any() else 0:.2%} "
          f"actual={((pnl_s>0).sum() / len(pnl_s)):.2%} PnL={pnl_s.sum():.1f} Sharpe={s['sharpe']:.3f}")

# --- Fixed TP reference (replay on OOS period) ---
# Re-run fixed TPs on OOS trades using MFE comparison
for tp_mult in FIXED_TP_SIZES:
    pnl_list = []
    for _, rec in oos_df.iterrows():
        tp_pts = rec['orbRange'] * tp_mult
        sl_dist = rec['sl_dist']
        if tp_pts <= rec['mfe']:
            pnl_list.append(tp_pts)
        elif rec['trade_result'] == 'SL':
            pnl_list.append(-sl_dist)
        else:
            pnl_list.append(0.0)
    pnl_s = pd.Series(pnl_list)
    s = calc_stats(pnl_s, f'Fixed TP {tp_mult}R')
    s['type']  = 'Fixed'
    s['scale'] = tp_mult
    compare_rows.append(s)
    eq_fixed = oos_df[['date']].copy()
    eq_fixed['pnl'] = pnl_list
    eq_fixed = eq_fixed.sort_values('date')
    eq_fixed['cum_pnl'] = eq_fixed['pnl'].cumsum().values
    equity_curves[f'Fixed {tp_mult}R'] = eq_fixed

compare_df = pd.DataFrame(compare_rows)

print("\n  === Summary: ML Dynamic TP vs Fixed TP ===")
print(f"  {'Label':<25} {'N':>6} {'WinRate':>9} {'TotalPnL':>10} {'Sharpe':>8} {'MaxDD':>8} {'PF':>7}")
print("  " + "-" * 75)
for _, r in compare_df.iterrows():
    print(f"  {r['label']:<25} {int(r['n']):>6} {r['wr']:>9.2%} {r['total']:>10.1f} "
          f"{r['sharpe']:>8.3f} {r['maxdd']:>8.1f} {r['pf']:>7.3f}")

# Save
compare_df.to_csv(os.path.join(OUTPUT_DIR, 'dynamic_tp_compare.csv'), index=False)
fi_avg.to_csv(os.path.join(OUTPUT_DIR, 'feature_importance.csv'), index=False)
oos_df.to_csv(os.path.join(OUTPUT_DIR, 'oos_trades_with_mfe.csv'), index=False)

# =============================================================================
# --- PHASE 5: DASHBOARD ---
# =============================================================================
print("\nPHASE 5: Building dashboard...")

DARK_BG  = "#0f1117"
CARD_BG  = "#1a1d27"
ACCENT   = "#7c6fff"
GREEN    = "#22d3a0"
RED_CLR  = "#f87171"
GOLD     = "#fbbf24"
BLUE_CLR = "#38bdf8"
TEXT_CLR = "#e2e8f0"

# Colour palette
PALETTE = {
    f'ML x{s}': c for s, c in zip(SCALE_FACTORS,
        [GREEN, '#22c4d3', ACCENT, GOLD, BLUE_CLR])
}
PALETTE.update({f'Fixed {t}R': c for t, c in zip(FIXED_TP_SIZES,
    ['#f87171', '#fb923c', '#a3a3a3', '#6b7280'])})

# --- Fig 1: Equity Curves ---
fig_eq = go.Figure()
for key, eq in equity_curves.items():
    is_ml = 'ML' in key
    fig_eq.add_trace(go.Scatter(
        x=pd.to_datetime(eq['date']), y=eq['cum_pnl'],
        mode='lines', name=key,
        line=dict(color=PALETTE.get(key, '#888'),
                  width=2.5 if is_ml else 1.5,
                  dash='solid' if is_ml else 'dot'),
        opacity=1.0 if is_ml else 0.6,
    ))
fig_eq.update_layout(
    title="Equity Curves: ML Dynamic TP vs Fixed TP (OOS Period)",
    xaxis_title="Date", yaxis_title="Cumulative PnL (points)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"), height=460,
)

# --- Fig 2: Win Rate + Sharpe comparison bar ---
ml_rows    = compare_df[compare_df['type'] == 'ML_Dynamic'].copy()
fixed_rows = compare_df[compare_df['type'] == 'Fixed'].copy()

fig_compare = make_subplots(rows=1, cols=3,
    subplot_titles=["Win Rate", "Sharpe Ratio", "Total PnL"])

for row_data, color, offset in [(ml_rows, ACCENT, -0.2), (fixed_rows, GOLD, 0.2)]:
    fig_compare.add_trace(go.Bar(
        x=row_data['label'], y=row_data['wr'] * 100,
        name=row_data['type'].iloc[0], marker_color=color,
        text=row_data['wr'].map(lambda x: f"{x:.1%}"),
        textposition='outside',
    ), row=1, col=1)
    fig_compare.add_trace(go.Bar(
        x=row_data['label'], y=row_data['sharpe'],
        marker_color=color, showlegend=False,
        text=row_data['sharpe'].map(lambda x: f"{x:.2f}"),
        textposition='outside',
    ), row=1, col=2)
    fig_compare.add_trace(go.Bar(
        x=row_data['label'], y=row_data['total'],
        marker_color=[GREEN if v > 0 else RED_CLR for v in row_data['total']],
        showlegend=False,
        text=row_data['total'].map(lambda x: f"{x:.0f}"),
        textposition='outside',
    ), row=1, col=3)

fig_compare.add_hline(y=60, line_dash="dot", line_color=GREEN,
    annotation_text="Target 60% WR", row=1, col=1)
fig_compare.update_layout(
    title="ML Dynamic TP vs Fixed TP: Key Metrics", barmode='group',
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=11), height=480,
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"),
)
for ann in fig_compare.layout.annotations:
    ann.font.color = TEXT_CLR

# --- Fig 3: Feature Importance ---
fig_fi = go.Figure(go.Bar(
    x=fi_avg.sort_values('importance')['importance'],
    y=fi_avg.sort_values('importance')['feature'],
    orientation='h', marker_color=ACCENT,
    text=fi_avg.sort_values('importance')['importance'].round(4),
    textposition='outside',
))
fig_fi.update_layout(
    title="MFE Predictor: Feature Importance (Walk-Forward Average)",
    xaxis_title="Mean Importance", yaxis_title="",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13), height=460, margin=dict(l=200),
)

# --- Fig 4: MFE Predicted vs Actual scatter ---
fig_scatter = go.Figure()
fig_scatter.add_trace(go.Scatter(
    x=oos_df['mfe_pred'], y=oos_df['mfe'],
    mode='markers',
    marker=dict(color=ACCENT, size=4, opacity=0.4),
    name='Predicted vs Actual MFE',
))
max_val = max(oos_df['mfe_pred'].max(), oos_df['mfe'].max())
fig_scatter.add_trace(go.Scatter(
    x=[0, max_val], y=[0, max_val],
    mode='lines', line=dict(color=GREEN, dash='dash', width=1),
    name='Perfect Prediction',
))
fig_scatter.update_layout(
    title="MFE: Predicted vs Actual (OOS)",
    xaxis_title="Predicted MFE (pts)", yaxis_title="Actual MFE (pts)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13), height=430,
)

# --- Fig 5: Intraday ATR distribution & MFE correlation ---
fig_atr = make_subplots(rows=1, cols=2,
    subplot_titles=["Intraday ATR Distribution", "Intraday ATR vs MFE"])
fig_atr.add_trace(go.Histogram(
    x=records_df['intraday_atr'], nbinsx=40,
    marker_color=BLUE_CLR, opacity=0.8, name='Intraday ATR',
), row=1, col=1)
fig_atr.add_trace(go.Scatter(
    x=oos_df['intraday_atr'], y=oos_df['mfe'],
    mode='markers',
    marker=dict(color=GOLD, size=4, opacity=0.4),
    name='ATR vs MFE',
), row=1, col=2)
fig_atr.update_layout(
    title="Intraday ATR (ORB Window) Analysis",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12), height=400, showlegend=False,
)
for ann in fig_atr.layout.annotations:
    ann.font.color = TEXT_CLR

# --- Fig 6: Win Rate by scale factor ---
ml_compare = compare_df[compare_df['type'] == 'ML_Dynamic'].copy()
fig_wr = go.Figure()
fig_wr.add_trace(go.Scatter(
    x=ml_compare['scale'], y=ml_compare['wr'] * 100,
    mode='lines+markers+text',
    line=dict(color=GREEN, width=2.5),
    marker=dict(size=10),
    text=[f"{v:.1%}" for v in ml_compare['wr']],
    textposition='top center', name='Win Rate',
))
fig_wr.add_trace(go.Scatter(
    x=ml_compare['scale'], y=ml_compare['sharpe'],
    mode='lines+markers+text',
    line=dict(color=ACCENT, width=2.5),
    marker=dict(size=10),
    text=[f"{v:.2f}" for v in ml_compare['sharpe']],
    textposition='bottom center', name='Sharpe',
    yaxis='y2',
))
fig_wr.add_hline(y=60, line_dash="dot", line_color=GREEN,
    annotation_text="60% WR target")
fig_wr.update_layout(
    title="ML Dynamic TP: Win Rate & Sharpe by Scale Factor",
    xaxis_title="Scale Factor (TP = MFE_pred × scale)",
    yaxis=dict(title="Win Rate (%)", color=GREEN),
    yaxis2=dict(title="Sharpe", overlaying='y', side='right', color=ACCENT),
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"), height=400,
)

# === Assemble HTML ===
# Best ML config
best_ml_row = ml_compare.sort_values('sharpe', ascending=False).iloc[0]

html_parts = [f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ORB ML Dynamic TP Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:{DARK_BG};color:{TEXT_CLR};padding:0 0 60px}}
    .hero{{background:linear-gradient(135deg,#1a1d27 0%,#12151f 60%,#0f1117 100%);
           border-bottom:1px solid #1e2130;padding:48px 40px 36px}}
    .hero h1{{font-size:28px;font-weight:700;margin-bottom:8px}}
    .hero p{{color:#94a3b8;font-size:15px;max-width:760px}}
    .badge{{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12px;
            font-weight:600;margin-left:8px;vertical-align:middle}}
    .badge-p{{background:#0d2e1f;color:{GREEN}}}
    .container{{max-width:1400px;margin:0 auto;padding:0 32px}}
    .card{{background:{CARD_BG};border-radius:12px;padding:28px 32px;margin:20px 0;
           border:1px solid #2a2d3a;box-shadow:0 4px 24px rgba(0,0,0,.4)}}
    .card h2{{margin:0 0 6px;color:{ACCENT};font-size:18px;letter-spacing:.5px}}
    .card p{{color:#94a3b8;font-size:14px;margin:4px 0 16px}}
    .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;margin:16px 0}}
    .kpi{{background:#12151f;border-radius:10px;padding:18px 20px;border:1px solid #1e2130}}
    .kpi .val{{font-size:24px;font-weight:700}}.kpi .lbl{{font-size:11px;color:#6b7280;margin-top:4px}}
    .green .val{{color:{GREEN}}}.red .val{{color:{RED_CLR}}}
    .gold .val{{color:{GOLD}}}.blue .val{{color:{ACCENT}}}
    table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}}
    th{{background:#12151f;color:{ACCENT};padding:10px 14px;text-align:left;border-bottom:2px solid #1e2130}}
    td{{padding:9px 14px;border-bottom:1px solid #1e2130}}
    tr:hover td{{background:#12151f}}
    .pos{{color:{GREEN};font-weight:600}}.neg{{color:{RED_CLR};font-weight:600}}
  </style>
</head>
<body>
<div class="hero"><div class="container">
  <h1>ORB + VWAP Retest — ML Dynamic TP
    <span class="badge badge-p">High Win Rate Mode</span>
  </h1>
  <p>開盤 ATR + ORB 結構特徵 → XGBoost 預測每筆交易的 MFE（最大有利浮盈）→
     動態設置 TP = MFE_pred × scale，實現<b>高勝率</b>策略。
     Walk-Forward 驗證，避免未來資訊洩漏。</p>
</div></div>
<div class="container">
<div class="card">
  <h2>Best ML Config: Scale = {best_ml_row['scale']}</h2>
  <p>OOS Period | Vs Best Fixed TP Reference</p>
  <div class="kpi-grid">
    <div class="kpi green"><div class="val">{best_ml_row['wr']:.1%}</div>
      <div class="lbl">ML Win Rate</div></div>
    <div class="kpi {'green' if best_ml_row['total']>0 else 'red'}">
      <div class="val">{best_ml_row['total']:.0f}</div>
      <div class="lbl">ML Total PnL (pts)</div></div>
    <div class="kpi gold"><div class="val">{best_ml_row['sharpe']:.3f}</div>
      <div class="lbl">ML Sharpe</div></div>
    <div class="kpi blue"><div class="val">{int(best_ml_row['n'])}</div>
      <div class="lbl">ML Trades</div></div>
    <div class="kpi {'green' if best_ml_row['maxdd']>-500 else 'red'}">
      <div class="val">{best_ml_row['maxdd']:.0f}</div>
      <div class="lbl">Max Drawdown</div></div>
    <div class="kpi gold"><div class="val">{best_ml_row['pf']:.3f}</div>
      <div class="lbl">Profit Factor</div></div>
  </div>
</div>
"""]

for fig_obj in [fig_eq, fig_wr, fig_compare, fig_fi, fig_scatter, fig_atr]:
    html_parts.append(f"<div style='margin:20px 0'>{fig_obj.to_html(full_html=False, include_plotlyjs='cdn')}</div>")

# Full table
html_parts.append("""<div class="card"><h2>Full Results Table</h2>
<table><thead><tr>
  <th>Strategy</th><th>Trades</th><th>Win Rate</th>
  <th>Total PnL</th><th>Avg PnL</th><th>Sharpe</th><th>Max DD</th><th>PF</th>
</tr></thead><tbody>""")
for _, r in compare_df.sort_values(['type', 'scale']).iterrows():
    pnl_cls = 'pos' if r['total'] > 0 else 'neg'
    html_parts.append(f"""<tr>
      <td>{'🤖 ' if r['type']=='ML_Dynamic' else '📌 '}{r['label']}</td>
      <td>{int(r['n'])}</td><td>{r['wr']:.2%}</td>
      <td class="{pnl_cls}">{r['total']:.1f}</td>
      <td>{r['avg']:.2f}</td><td>{r['sharpe']:.3f}</td>
      <td class="neg">{r['maxdd']:.1f}</td>
      <td>{r['pf']:.3f}</td></tr>""")
html_parts.append("</tbody></table></div></div></body></html>")

out_html = os.path.join(OUTPUT_DIR, 'ml_dynamic_tp_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write('\n'.join(html_parts))

print(f"\n{'='*60}")
print("DONE.")
print(f"  Dashboard : {out_html}")
print(f"  Compare   : {os.path.join(OUTPUT_DIR, 'dynamic_tp_compare.csv')}")
print(f"  Features  : {os.path.join(OUTPUT_DIR, 'feature_importance.csv')}")
print("="*60)
