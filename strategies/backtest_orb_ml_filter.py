"""
ORB + VWAP Retest Backtest with Machine Learning Filter
=======================================================
基於開盤 Range 結構特徵，使用 Walk-Forward XGBoost 分類器過濾交易，
對比 ML 過濾前後的績效差異。

依賴: pip install xgboost scikit-learn databento plotly pandas numpy
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
from datetime import time, timedelta, date

# ML Libraries
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\ml_filter"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Strategy Parameters
ORB_MIN = 30                      # 30-minute ORB (09:30 - 10:00)
LABEL_TP_SIZE = 1.0               # TP 倍數用於 Win/Loss 標籤
TP_SIZES = [0.5, 0.8, 1.0, 1.5, 2.0]  # 績效報告用全 TP 範圍
SESSION_START = time(9, 30)
SESSION_ENTRY_CUTOFF = time(12, 0)
SESSION_FORCE_EXIT = time(15, 55)

# ML Walk-Forward Parameters
WALK_FORWARD_TRAIN_YEARS = 3      # 每次訓練用 3 年歷史
WALK_FORWARD_TEST_YEARS = 1       # 每次驗證 1 年
ML_PROB_THRESHOLDS = [0.50, 0.55, 0.60, 0.65]  # 過濾門檻

# Feature columns used for ML
FEATURE_COLS = [
    'orb_range',
    'orb_range_vs_atr',
    'orb_range_percentile',
    'orb_volume_vs_avg',
    'gap_pct',
    'orb_vs_prev_high',
    'orb_vs_prev_low',
    'vwap_vs_orbmid',
    'orb_momentum_pct',
    'orb_body_ratio',
    'orb_first_bar_dir',
    'day_of_week',
]

pio.templates.default = "plotly_dark"

# =============================================================================
# --- PHASE 1: DATA LOADING & PREPROCESSING ---
# =============================================================================
print("=" * 60)
print("PHASE 1: Loading and preprocessing data...")
print("=" * 60)

store = db.DBNStore.from_file(FILE_PATH)
df_1m = store.to_df()
df_1m.index = pd.to_datetime(df_1m.index).tz_convert('US/Eastern')
df_1m.sort_index(inplace=True)

# Filter to standard NQ outrights only
df_1m = df_1m[df_1m['symbol'].astype(str).str.match(r'^NQ[HMUZ]\d$')].copy()

df_1m['date'] = df_1m.index.date
df_1m['time'] = df_1m.index.time

# Front-month routing via highest daily volume
daily_vol = df_1m.groupby(['date', 'symbol'])['volume'].sum().reset_index()
front_months = daily_vol.loc[daily_vol.groupby('date')['volume'].idxmax()][['date', 'symbol']]
df_1m = df_1m.reset_index().merge(front_months, on=['date', 'symbol'], how='inner')
df_1m.set_index('ts_event', inplace=True)
df_1m.sort_index(inplace=True)

print(f"  Rows after front-month filter: {len(df_1m):,}")

# HLC3 and VWAP
df_1m['hlc3'] = (df_1m['high'] + df_1m['low'] + df_1m['close']) / 3.0
rth_mask = df_1m.index.time >= time(9, 30)
df_1m.loc[rth_mask, 'pVol'] = df_1m[rth_mask]['hlc3'] * df_1m[rth_mask]['volume']
df_1m['vwap'] = np.nan
grouped_rth = df_1m[rth_mask].groupby('date')
rth_vwap_val = grouped_rth['pVol'].cumsum() / grouped_rth['volume'].cumsum()
df_1m.loc[rth_mask, 'vwap'] = rth_vwap_val
df_1m['vwap'] = df_1m.groupby('date')['vwap'].ffill().ffill()

# Previous day OHLC for feature engineering
daily_ohlc = (
    df_1m[df_1m.index.time >= time(9, 30)]
    .groupby('date')
    .agg(daily_high=('high', 'max'), daily_low=('low', 'min'),
         daily_close=('close', 'last'), daily_open=('open', 'first'),
         daily_volume=('volume', 'sum'))
    .reset_index()
)
daily_ohlc['prev_high']   = daily_ohlc['daily_high'].shift(1)
daily_ohlc['prev_low']    = daily_ohlc['daily_low'].shift(1)
daily_ohlc['prev_close']  = daily_ohlc['daily_close'].shift(1)
daily_ohlc['prev_volume'] = daily_ohlc['daily_volume'].shift(1)

# ATR (14-day)
daily_ohlc['tr'] = np.maximum(
    daily_ohlc['daily_high'] - daily_ohlc['daily_low'],
    np.maximum(
        abs(daily_ohlc['daily_high'] - daily_ohlc['prev_close']),
        abs(daily_ohlc['daily_low']  - daily_ohlc['prev_close'])
    )
)
daily_ohlc['atr_14'] = daily_ohlc['tr'].rolling(14, min_periods=3).mean()

# Average ORB volume (rolling 20-day) — computed after ORB extraction below
dates = sorted(df_1m['date'].unique())
print(f"  Total trading days: {len(dates)}")

# =============================================================================
# --- PHASE 2: ORB FEATURE EXTRACTION + BACKTEST ---
# =============================================================================
print("\nPHASE 2: Running backtest + feature extraction...")

daily_ohlc_dict = daily_ohlc.set_index('date').to_dict('index')

all_trades = []    # Full trade log (one row per trade per tp_size)
orb_features = []  # One row per trading day with ORB structure features

for i, trade_date in enumerate(dates):
    day_str = trade_date.strftime('%Y-%m-%d')

    try:
        day_data = df_1m.loc[day_str]
    except KeyError:
        continue
    if day_data.empty:
        continue

    prev_info = daily_ohlc_dict.get(trade_date, {})
    prev_close  = prev_info.get('prev_close', np.nan)
    prev_high   = prev_info.get('prev_high', np.nan)
    prev_low    = prev_info.get('prev_low', np.nan)
    atr_14      = prev_info.get('atr_14', np.nan)
    today_open  = prev_info.get('daily_open', np.nan)

    orb_end_dt = pd.Timestamp(f"{day_str} 09:30:00", tz='US/Eastern') + pd.Timedelta(minutes=ORB_MIN)
    orb_end_time = orb_end_dt.time()

    # ---- ORB bars ----
    orb_mask = (day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)
    orb_bars = day_data[orb_mask]
    if orb_bars.empty or len(orb_bars) < 3:
        continue

    orbH = orb_bars['high'].max()
    orbL = orb_bars['low'].min()
    orbRange = orbH - orbL
    if orbRange <= 0:
        continue

    orb_open    = orb_bars['open'].iloc[0]
    orb_close   = orb_bars['close'].iloc[-1]
    orb_volume  = orb_bars['volume'].sum()

    # Last 5-min candle body ratio within ORB
    last_5m_bars = orb_bars[orb_bars.index.minute % 5 == 4]
    if not last_5m_bars.empty:
        lb = last_5m_bars.iloc[-1]
        last_body = abs(lb['close'] - lb['open'])
        last_range = lb['high'] - lb['low']
        orb_body_ratio = last_body / last_range if last_range > 0 else 0.5
    else:
        orb_body_ratio = 0.5

    # VWAP position at ORB end
    vwap_at_orb_end = orb_bars['vwap'].iloc[-1]
    orb_mid = (orbH + orbL) / 2.0
    vwap_vs_orbmid = (vwap_at_orb_end - orb_mid) / orbRange  # >0 = VWAP above mid

    # Feature values
    gap_pct         = (today_open - prev_close) / prev_close if prev_close > 0 else 0
    orb_range_vs_atr = orbRange / atr_14 if atr_14 > 0 else np.nan
    orb_momentum_pct = (orb_close - orb_open) / orb_open if orb_open > 0 else 0
    orb_first_bar_dir = 1 if orb_bars['close'].iloc[0] >= orb_bars['open'].iloc[0] else -1
    orb_vs_prev_high  = 1 if orbH >= prev_high else 0
    orb_vs_prev_low   = 1 if orbL <= prev_low else 0
    day_of_week       = trade_date.weekday()

    orb_features.append({
        'date'               : trade_date,
        'orb_range'          : orbRange,
        'orb_range_vs_atr'   : orb_range_vs_atr,
        'orb_volume'         : orb_volume,
        'gap_pct'            : gap_pct,
        'orb_vs_prev_high'   : orb_vs_prev_high,
        'orb_vs_prev_low'    : orb_vs_prev_low,
        'vwap_vs_orbmid'     : vwap_vs_orbmid,
        'orb_momentum_pct'   : orb_momentum_pct,
        'orb_body_ratio'     : orb_body_ratio,
        'orb_first_bar_dir'  : orb_first_bar_dir,
        'day_of_week'        : day_of_week,
        'orbH'               : orbH,
        'orbL'               : orbL,
    })

    # ---- Entry scan ----
    entry_window = day_data[
        (day_data['time'] >= orb_end_time) &
        (day_data['time'] <= SESSION_ENTRY_CUTOFF)
    ]
    if entry_window.empty:
        continue

    has_traded   = False
    pending_long = False
    pending_short = False
    entry_price  = 0.0
    entry_time   = None
    entry_dir    = None
    sl_price     = 0.0
    break_bar_num = 0
    bar_cnt       = 0

    for idx, row in entry_window.iterrows():
        if has_traded:
            break
        bar_cnt += 1
        was_pl = pending_long
        was_ps = pending_short

        if not pending_long and not pending_short:
            if idx.minute % 5 == 4:
                if row['close'] > orbH:
                    pending_long  = True
                    break_bar_num = bar_cnt
                if row['close'] < orbL:
                    pending_short = True
                    break_bar_num = bar_cnt

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

    # ---- Exit scan for each TP ----
    try:
        exit_idx_pos = day_data.index.get_loc(entry_time) + 1
        exit_path = day_data.iloc[exit_idx_pos:] if exit_idx_pos < len(day_data) else pd.DataFrame()
    except Exception:
        exit_path = pd.DataFrame()

    for tp_size in TP_SIZES:
        tp_price = (orbH + orbRange * tp_size) if entry_dir == 'Long' else (orbL - orbRange * tp_size)

        exit_price_val = None
        exit_time_val  = None
        exit_reason    = "EOD"

        for e_idx, e_row in exit_path.iterrows():
            if e_row['time'] >= SESSION_FORCE_EXIT:
                exit_price_val = e_row['close']
                exit_time_val  = e_idx
                exit_reason    = "TimeClose"
                break
            if entry_dir == 'Long':
                if e_row['low'] <= sl_price:
                    exit_price_val = sl_price;  exit_time_val = e_idx; exit_reason = "SL";  break
                elif e_row['high'] >= tp_price:
                    exit_price_val = tp_price;  exit_time_val = e_idx; exit_reason = "TP";  break
            else:
                if e_row['high'] >= sl_price:
                    exit_price_val = sl_price;  exit_time_val = e_idx; exit_reason = "SL";  break
                elif e_row['low'] <= tp_price:
                    exit_price_val = tp_price;  exit_time_val = e_idx; exit_reason = "TP";  break

        if exit_time_val is None:
            exit_price_val = exit_path.iloc[-1]['close'] if not exit_path.empty else entry_price
            exit_reason    = "EOD"

        pnl = (exit_price_val - entry_price) if entry_dir == 'Long' else (entry_price - exit_price_val)

        all_trades.append({
            'date'          : trade_date,
            'tp_size'       : tp_size,
            'direction'     : entry_dir,
            'entry_time'    : entry_time,
            'entry_price'   : entry_price,
            'exit_reason'   : exit_reason,
            'pnl'           : pnl,
            'break_bar_num' : break_bar_num,
        })

print(f"  Total trades recorded: {len(all_trades)}")
print(f"  Days with valid ORB features: {len(orb_features)}")

# =============================================================================
# --- BUILD FEATURE DATAFRAME ---
# =============================================================================
feat_df = pd.DataFrame(orb_features)
feat_df['date'] = pd.to_datetime(feat_df['date'])

# Rolling percentile of ORB range (20-day lookback)
feat_df.sort_values('date', inplace=True)
feat_df['orb_range_percentile'] = feat_df['orb_range'].rolling(20, min_periods=5).rank(pct=True)

# Rolling average ORB volume (20-day)
feat_df['orb_volume_avg_20'] = feat_df['orb_volume'].rolling(20, min_periods=5).mean()
feat_df['orb_volume_vs_avg'] = feat_df['orb_volume'] / feat_df['orb_volume_avg_20'].replace(0, np.nan)

# Merge trade results (use LABEL_TP_SIZE for y labels)
trade_df = pd.DataFrame(all_trades)
trade_df['date'] = pd.to_datetime(trade_df['date'])

label_trades = trade_df[trade_df['tp_size'] == LABEL_TP_SIZE][['date', 'pnl']].copy()
label_trades['label'] = (label_trades['pnl'] > 0).astype(int)

merged_df = feat_df.merge(label_trades[['date', 'label', 'pnl']], on='date', how='inner')
merged_df.dropna(subset=FEATURE_COLS, inplace=True)
merged_df.reset_index(drop=True, inplace=True)

print(f"\n  Merged ML dataset: {len(merged_df)} rows")
print(f"  Win rate (baseline): {merged_df['label'].mean():.2%}")

# =============================================================================
# --- PHASE 3: WALK-FORWARD ML TRAINING ---
# =============================================================================
print("\nPHASE 3: Walk-Forward ML training (XGBoost)...")

merged_df['date'] = pd.to_datetime(merged_df['date'])
merged_df['year'] = merged_df['date'].dt.year

all_years = sorted(merged_df['year'].unique())
min_year  = all_years[0]
max_year  = all_years[-1]

# Walk-Forward: train on TRAIN_YEARS, test on next TEST_YEARS
test_start_year = min_year + WALK_FORWARD_TRAIN_YEARS
walk_forward_results = []

merged_df['ml_prob_win']  = np.nan
merged_df['ml_pred_label'] = np.nan
merged_df['wf_fold']      = np.nan

fold = 0
for test_year_start in range(test_start_year, max_year + 1, WALK_FORWARD_TEST_YEARS):
    test_year_end   = test_year_start + WALK_FORWARD_TEST_YEARS - 1
    train_year_end  = test_year_start - 1
    train_year_start = test_year_start - WALK_FORWARD_TRAIN_YEARS

    train_mask = (merged_df['year'] >= train_year_start) & (merged_df['year'] <= train_year_end)
    test_mask  = (merged_df['year'] >= test_year_start)  & (merged_df['year'] <= test_year_end)

    X_train = merged_df.loc[train_mask, FEATURE_COLS]
    y_train = merged_df.loc[train_mask, 'label']
    X_test  = merged_df.loc[test_mask, FEATURE_COLS]
    y_test  = merged_df.loc[test_mask, 'label']

    if len(X_train) < 30 or len(X_test) < 5:
        continue

    # Replace NaN with median from training set
    train_medians = X_train.median()
    X_train_filled = X_train.fillna(train_medians)
    X_test_filled  = X_test.fillna(train_medians)

    # XGBoost classifier (conservative settings to prevent overfitting)
    model = XGBClassifier(
        n_estimators=150,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        scale_pos_weight=(y_train == 0).sum() / max((y_train == 1).sum(), 1),
        use_label_encoder=False,
        eval_metric='logloss',
        verbosity=0,
        random_state=42,
    )
    model.fit(X_train_filled, y_train)

    probs  = model.predict_proba(X_test_filled)[:, 1]
    preds  = (probs >= 0.50).astype(int)

    merged_df.loc[test_mask, 'ml_prob_win']   = probs
    merged_df.loc[test_mask, 'ml_pred_label'] = preds
    merged_df.loc[test_mask, 'wf_fold']       = fold

    # Collect feature importance for this fold
    fi = pd.DataFrame({
        'feature'    : FEATURE_COLS,
        'importance' : model.feature_importances_,
        'fold'       : fold,
        'test_years' : f"{test_year_start}-{test_year_end}"
    })
    walk_forward_results.append(fi)

    n_test  = len(X_test)
    try:
        auc = roc_auc_score(y_test, probs)
    except Exception:
        auc = np.nan
    win_rate_test = y_test.mean()
    print(f"  Fold {fold}: Train {train_year_start}-{train_year_end} | "
          f"Test {test_year_start}-{test_year_end} | "
          f"n={n_test} | WinRate={win_rate_test:.2%} | AUC={auc:.3f}")
    fold += 1

print(f"  Walk-forward complete: {fold} folds")

# Aggregate feature importance across folds
fi_all = pd.concat(walk_forward_results, ignore_index=True)
fi_avg = fi_all.groupby('feature')['importance'].mean().reset_index().sort_values('importance', ascending=False)

# =============================================================================
# --- PHASE 4: PERFORMANCE COMPARISON (ML-filtered vs Baseline) ---
# =============================================================================
print("\nPHASE 4: Comparing filtered vs baseline performance...")

# Only compare on the OOS test period (rows with ml_prob_win filled)
oos_merged = merged_df.dropna(subset=['ml_prob_win']).copy()
oos_trades  = trade_df[trade_df['date'].isin(oos_merged['date'])].copy()

def calc_stats(pnl_series: pd.Series, label: str = "") -> dict:
    """Compute standard performance metrics."""
    n     = len(pnl_series)
    wins  = (pnl_series > 0).sum()
    total = pnl_series.sum()
    wr    = wins / n if n > 0 else 0
    avg   = pnl_series.mean() if n > 0 else 0
    std   = pnl_series.std() if n > 1 else 1
    # Sharpe (annualized, assuming ~252 trading days)
    sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
    # Max Drawdown
    cum = pnl_series.cumsum()
    roll_max = cum.cummax()
    drawdown = (cum - roll_max)
    max_dd = drawdown.min()
    profit_factor = pnl_series[pnl_series > 0].sum() / abs(pnl_series[pnl_series < 0].sum()) if (pnl_series < 0).sum() > 0 else np.inf
    return {
        'Label'         : label,
        'Trades'        : n,
        'WinRate'       : wr,
        'TotalPnL'      : total,
        'AvgPnL'        : avg,
        'Sharpe'        : sharpe,
        'MaxDrawdown'   : max_dd,
        'ProfitFactor'  : profit_factor,
    }

comparison_rows = []
equity_curves   = {}

# Build probability lookup per date
prob_lookup = oos_merged.set_index('date')['ml_prob_win'].to_dict()

for tp_size in TP_SIZES:
    tp_trades = oos_trades[oos_trades['tp_size'] == tp_size].copy()
    tp_trades = tp_trades.sort_values('date')
    tp_trades['ml_prob'] = tp_trades['date'].map(prob_lookup)

    # Baseline (no filter)
    baseline_stats = calc_stats(tp_trades['pnl'], f"Baseline TP={tp_size}")
    baseline_stats['TP_Size'] = tp_size
    baseline_stats['Threshold'] = 'None'
    comparison_rows.append(baseline_stats)

    eq_key = f"Baseline_TP{tp_size}"
    equity_curves[eq_key] = tp_trades[['date', 'pnl']].copy()
    equity_curves[eq_key]['cum_pnl'] = tp_trades['pnl'].cumsum().values

    for thresh in ML_PROB_THRESHOLDS:
        filtered = tp_trades[tp_trades['ml_prob'] >= thresh].copy()
        if len(filtered) < 5:
            continue
        stats = calc_stats(filtered['pnl'], f"ML≥{thresh} TP={tp_size}")
        stats['TP_Size']   = tp_size
        stats['Threshold'] = thresh
        comparison_rows.append(stats)

        if tp_size == LABEL_TP_SIZE:
            eq_key = f"ML_{thresh}_TP{tp_size}"
            equity_curves[eq_key] = filtered[['date', 'pnl']].copy()
            equity_curves[eq_key]['cum_pnl'] = filtered['pnl'].cumsum().values

compare_df = pd.DataFrame(comparison_rows)
compare_df.to_csv(os.path.join(OUTPUT_DIR, 'ml_performance_compare.csv'), index=False)
fi_avg.to_csv(os.path.join(OUTPUT_DIR, 'ml_feature_importance.csv'), index=False)
merged_df.to_csv(os.path.join(OUTPUT_DIR, 'ml_raw_trades_with_features.csv'), index=False)
print("  CSVs saved.")

# =============================================================================
# --- PHASE 5: PLOTLY HTML DASHBOARD ---
# =============================================================================
print("\nPHASE 5: Generating dashboard...")

DARK_BG  = "#0f1117"
CARD_BG  = "#1a1d27"
ACCENT   = "#7c6fff"
GREEN    = "#22d3a0"
RED_CLR  = "#f87171"
GOLD     = "#fbbf24"
TEXT_CLR = "#e2e8f0"

# --- Fig 1: Equity Curves for LABEL_TP_SIZE ---
fig_eq = go.Figure()
palette = [ACCENT, GREEN, RED_CLR, GOLD, "#38bdf8", "#fb923c"]
for j, (key, eq_data) in enumerate(equity_curves.items()):
    is_baseline = 'Baseline' in key
    fig_eq.add_trace(go.Scatter(
        x=eq_data['date'], y=eq_data['cum_pnl'],
        mode='lines', name=key,
        line=dict(color=palette[j % len(palette)],
                  width=2.5 if is_baseline else 1.8,
                  dash='dot' if is_baseline else 'solid'),
        opacity=0.9 if is_baseline else 1.0,
    ))
fig_eq.update_layout(
    title=f"Equity Curves: Baseline vs ML Filter (TP={LABEL_TP_SIZE}R) — OOS Period",
    xaxis_title="Date", yaxis_title="Cumulative PnL (points)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"),
    height=450,
)

# --- Fig 2: Performance Comparison Heatmap (grouped bar) ---
# Pivot: rows=TP_Size, cols=Threshold, values=WinRate / TotalPnL / Sharpe
pivot_tp = compare_df[compare_df['TP_Size'] == LABEL_TP_SIZE].copy()
pivot_tp['Threshold'] = pivot_tp['Threshold'].astype(str)

metrics_to_show = ['WinRate', 'TotalPnL', 'Sharpe', 'MaxDrawdown', 'Trades', 'ProfitFactor']
fig_bar = make_subplots(rows=2, cols=3,
    subplot_titles=metrics_to_show,
    vertical_spacing=0.18, horizontal_spacing=0.10)

colors_bar = [ACCENT, GREEN, GOLD, RED_CLR, "#38bdf8", "#fb923c"]
for idx, metric in enumerate(metrics_to_show):
    row_i = idx // 3 + 1
    col_i = idx % 3 + 1
    for j, thresh in enumerate(pivot_tp['Threshold'].unique()):
        sub = pivot_tp[pivot_tp['Threshold'] == thresh]
        label = "Baseline" if thresh == 'None' else f"ML≥{thresh}"
        fig_bar.add_trace(go.Bar(
            x=[label], y=[sub[metric].values[0]],
            name=label, marker_color=colors_bar[j],
            showlegend=(idx == 0),
            text=[f"{sub[metric].values[0]:.3f}"],
            textposition='outside', textfont=dict(size=11),
        ), row=row_i, col=col_i)

fig_bar.update_layout(
    title=f"Performance Metrics by ML Threshold (TP={LABEL_TP_SIZE}R)",
    barmode='group',
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"),
    height=580,
)
for ann in fig_bar.layout.annotations:
    ann.font.color = TEXT_CLR

# --- Fig 3: Feature Importance ---
fig_fi = go.Figure(go.Bar(
    x=fi_avg.sort_values('importance')['importance'],
    y=fi_avg.sort_values('importance')['feature'],
    orientation='h',
    marker_color=ACCENT,
    text=fi_avg.sort_values('importance')['importance'].round(4),
    textposition='outside',
))
fig_fi.update_layout(
    title="Average Feature Importance (Walk-Forward XGBoost)",
    xaxis_title="Mean Importance", yaxis_title="Feature",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    height=480,
    margin=dict(l=180),
)

# --- Fig 4: ML Probability distribution (Win vs Loss) ---
prob_win  = oos_merged[oos_merged['label'] == 1]['ml_prob_win'].dropna()
prob_loss = oos_merged[oos_merged['label'] == 0]['ml_prob_win'].dropna()

fig_dist = go.Figure()
fig_dist.add_trace(go.Histogram(x=prob_win,  name='Win',  nbinsx=20,
                                 marker_color=GREEN,   opacity=0.75))
fig_dist.add_trace(go.Histogram(x=prob_loss, name='Loss', nbinsx=20,
                                 marker_color=RED_CLR, opacity=0.75))
fig_dist.update_layout(
    barmode='overlay',
    title="ML P(Win) Distribution: Actual Win vs Loss Trades",
    xaxis_title="Predicted P(Win)", yaxis_title="Count",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG),
    height=380,
)

# --- Fig 5: Win Rate vs P(Win) Bucket ---
oos_merged['prob_bucket'] = pd.cut(oos_merged['ml_prob_win'], bins=10)
bucket_wr = oos_merged.groupby('prob_bucket')['label'].agg(['mean', 'count']).reset_index()
bucket_wr.columns = ['bucket', 'win_rate', 'count']
bucket_wr['bucket_str'] = bucket_wr['bucket'].astype(str)

fig_cal = make_subplots(specs=[[{"secondary_y": True}]])
fig_cal.add_trace(go.Bar(x=bucket_wr['bucket_str'], y=bucket_wr['win_rate'],
                          name='Win Rate', marker_color=ACCENT, opacity=0.85), secondary_y=False)
fig_cal.add_trace(go.Scatter(x=bucket_wr['bucket_str'], y=bucket_wr['count'],
                              name='# Trades', mode='lines+markers',
                              line=dict(color=GOLD, width=2),
                              marker=dict(size=7)), secondary_y=True)
fig_cal.update_layout(
    title="Calibration: Actual Win Rate per P(Win) Bucket",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12),
    legend=dict(bgcolor=CARD_BG),
    height=380,
)
fig_cal.update_yaxes(title_text="Win Rate", secondary_y=False)
fig_cal.update_yaxes(title_text="# Trades",  secondary_y=True)

# --- Assemble HTML ---
def section(title: str, subtitle: str = "") -> str:
    sub_html = f"<p style='color:#94a3b8;margin:4px 0 12px;font-size:14px'>{subtitle}</p>" if subtitle else ""
    return f"""
    <div style='background:{CARD_BG};border-radius:12px;padding:28px 32px;margin:20px 0;
                border:1px solid #2a2d3a;box-shadow:0 4px 24px rgba(0,0,0,0.4)'>
        <h2 style='margin:0 0 6px;color:{ACCENT};font-size:18px;letter-spacing:.5px'>{title}</h2>
        {sub_html}
    """

html_parts = [f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ORB ML Filter — Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: {DARK_BG};
      color: {TEXT_CLR};
      min-height: 100vh;
      padding: 0 0 60px;
    }}
    .hero {{
      background: linear-gradient(135deg,#1a1d27 0%,#12151f 60%,#0f1117 100%);
      border-bottom: 1px solid #1e2130;
      padding: 48px 40px 36px;
    }}
    .hero h1 {{ font-size: 28px; font-weight: 700; color: {TEXT_CLR}; margin-bottom: 8px; }}
    .hero p  {{ color: #94a3b8; font-size: 15px; max-width: 700px; }}
    .badge {{
      display:inline-block; padding:3px 10px; border-radius:99px;
      font-size:12px; font-weight:600; margin-left:10px; vertical-align:middle;
    }}
    .badge-blue  {{ background:#1e3a5f; color:#60a5fa; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px; margin: 20px 0;
    }}
    .kpi {{
      background: #12151f; border-radius: 10px; padding: 18px 20px;
      border: 1px solid #1e2130;
    }}
    .kpi .val {{ font-size: 26px; font-weight: 700; }}
    .kpi .lbl {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
    .kpi.green .val {{ color: {GREEN}; }}
    .kpi.red   .val {{ color: {RED_CLR}; }}
    .kpi.gold  .val {{ color: {GOLD}; }}
    .kpi.blue  .val {{ color: {ACCENT}; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 0 32px; }}
    table {{
      width: 100%; border-collapse: collapse; font-size: 13px;
      margin-top: 12px;
    }}
    th {{
      background: #12151f; color: {ACCENT};
      padding: 10px 14px; text-align: left; border-bottom: 2px solid #1e2130;
    }}
    td {{ padding: 9px 14px; border-bottom: 1px solid #1e2130; color: {TEXT_CLR}; }}
    tr:hover td {{ background: #12151f; }}
    .pos {{ color: {GREEN}; font-weight: 600; }}
    .neg {{ color: {RED_CLR}; font-weight: 600; }}
  </style>
</head>
<body>
<div class="hero">
  <div class="container">
    <h1>ORB + VWAP Retest — ML Filter Dashboard
      <span class="badge badge-blue">XGBoost Walk-Forward</span>
    </h1>
    <p>使用開盤 Range 結構特徵（Range 大小、成交量、動量、位置等）訓練分類器，
       在 OOS 期間動態過濾低勝算交易，提升策略績效。</p>
  </div>
</div>
<div class="container">
"""]

# KPI summary block
baseline_row = compare_df[
    (compare_df['TP_Size'] == LABEL_TP_SIZE) & (compare_df['Threshold'] == 'None')
].iloc[0]
best_sharpe_row = compare_df[compare_df['TP_Size'] == LABEL_TP_SIZE].sort_values('Sharpe', ascending=False).iloc[0]

html_parts.append(f"""
{section("📊 關鍵指標摘要", f"OOS 期間 | TP={LABEL_TP_SIZE}R | 最佳過濾: 閾值={best_sharpe_row['Threshold']}")}
<div class="kpi-grid">
  <div class="kpi blue"><div class="val">{int(baseline_row['Trades'])}</div><div class="lbl">Baseline 交易數</div></div>
  <div class="kpi {'green' if baseline_row['WinRate']>=0.5 else 'red'}">
    <div class="val">{baseline_row['WinRate']:.1%}</div><div class="lbl">Baseline 勝率</div></div>
  <div class="kpi {'green' if baseline_row['TotalPnL']>0 else 'red'}">
    <div class="val">{baseline_row['TotalPnL']:.1f}</div><div class="lbl">Baseline 總 PnL (pts)</div></div>
  <div class="kpi gold"><div class="val">{baseline_row['Sharpe']:.3f}</div><div class="lbl">Baseline Sharpe</div></div>
  <div class="kpi blue"><div class="val">{int(best_sharpe_row['Trades'])}</div><div class="lbl">ML過濾後 交易數</div></div>
  <div class="kpi {'green' if best_sharpe_row['WinRate']>=0.5 else 'red'}">
    <div class="val">{best_sharpe_row['WinRate']:.1%}</div><div class="lbl">ML過濾後 勝率</div></div>
  <div class="kpi {'green' if best_sharpe_row['TotalPnL']>0 else 'red'}">
    <div class="val">{best_sharpe_row['TotalPnL']:.1f}</div><div class="lbl">ML過濾後 總 PnL (pts)</div></div>
  <div class="kpi gold"><div class="val">{best_sharpe_row['Sharpe']:.3f}</div><div class="lbl">ML過濾後 Sharpe</div></div>
</div></div>
""")

# Charts
for fig_obj in [fig_eq, fig_bar, fig_fi, fig_dist, fig_cal]:
    html_parts.append(f"<div style='margin:20px 0'>{fig_obj.to_html(full_html=False, include_plotlyjs='cdn')}</div>")

# Full comparison table
html_parts.append(f"""
{section("📋 完整績效對比表", "所有 TP 倍數 × ML 閾值")}
<table>
<thead>
  <tr>
    <th>TP 倍數</th><th>ML 閾值</th><th>交易數</th>
    <th>勝率</th><th>總 PnL</th><th>平均 PnL</th>
    <th>Sharpe</th><th>最大回撤</th><th>獲利因子</th>
  </tr>
</thead>
<tbody>
""")
for _, r in compare_df.sort_values(['TP_Size','Threshold']).iterrows():
    pnl_cls = 'pos' if r['TotalPnL'] > 0 else 'neg'
    html_parts.append(f"""<tr>
      <td>{r['TP_Size']}</td><td>{r['Threshold']}</td><td>{int(r['Trades'])}</td>
      <td>{r['WinRate']:.2%}</td>
      <td class="{pnl_cls}">{r['TotalPnL']:.2f}</td>
      <td>{r['AvgPnL']:.3f}</td>
      <td>{r['Sharpe']:.3f}</td>
      <td class="neg">{r['MaxDrawdown']:.2f}</td>
      <td>{r['ProfitFactor']:.3f}</td>
    </tr>""")

html_parts.append("</tbody></table></div>")
html_parts.append("</div></body></html>")

out_html = os.path.join(OUTPUT_DIR, 'orb_ml_filter_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write('\n'.join(html_parts))

print(f"\n{'='*60}")
print("DONE. Outputs:")
print(f"  Dashboard  : {out_html}")
print(f"  Raw trades : {os.path.join(OUTPUT_DIR, 'ml_raw_trades_with_features.csv')}")
print(f"  Performance: {os.path.join(OUTPUT_DIR, 'ml_performance_compare.csv')}")
print(f"  Features   : {os.path.join(OUTPUT_DIR, 'ml_feature_importance.csv')}")
print("="*60)
