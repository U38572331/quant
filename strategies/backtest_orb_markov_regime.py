"""
ORB + VWAP Retest Backtest with Markov Regime Volatility Filter
================================================================
Uses a Hidden Markov Model (Gaussian HMM) to identify volatility regimes
(Low / Medium / High) from daily returns, then evaluates ORB strategy
performance conditional on each regime — enabling regime-based trade filtering.

Walk-forward approach: HMM is re-fit every year using only past data.

Dependencies: pip install hmmlearn statsmodels databento plotly pandas numpy
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

warnings.filterwarnings('ignore')

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\markov_regime"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Strategy Parameters
ORB_MIN = 30
TP_SIZES = [0.5, 0.8, 1.0, 1.5, 2.0]
SESSION_START = time(9, 30)
SESSION_ENTRY_CUTOFF = time(12, 0)
SESSION_FORCE_EXIT = time(15, 55)

# HMM Parameters
N_REGIMES = 3               # Low / Medium / High volatility
HMM_LOOKBACK_DAYS = 504     # ~2 years of trading days for HMM fitting
HMM_REFIT_FREQ = 'Y'        # Refit annually

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

# Front-month routing
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

# =============================================================================
# --- PHASE 2: DAILY OHLC + VOLATILITY FEATURES FOR HMM ---
# =============================================================================
print("\nPHASE 2: Building daily volatility features for HMM...")

rth_data = df_1m[df_1m.index.time >= time(9, 30)]
daily_ohlc = rth_data.groupby('date').agg(
    daily_open=('open', 'first'),
    daily_high=('high', 'max'),
    daily_low=('low', 'min'),
    daily_close=('close', 'last'),
    daily_volume=('volume', 'sum'),
).reset_index()
daily_ohlc['date'] = pd.to_datetime(daily_ohlc['date'])
daily_ohlc.sort_values('date', inplace=True)
daily_ohlc.reset_index(drop=True, inplace=True)

# Features for HMM: log returns + realized volatility (Parkinson)
daily_ohlc['log_return'] = np.log(daily_ohlc['daily_close'] / daily_ohlc['daily_close'].shift(1))
daily_ohlc['abs_return'] = daily_ohlc['log_return'].abs()
daily_ohlc['range_pct'] = (daily_ohlc['daily_high'] - daily_ohlc['daily_low']) / daily_ohlc['daily_close']

# Parkinson volatility estimator (rolling 5-day)
daily_ohlc['parkinson_vol'] = np.sqrt(
    (1 / (4 * np.log(2))) * (np.log(daily_ohlc['daily_high'] / daily_ohlc['daily_low'])) ** 2
)
daily_ohlc['parkinson_vol_5d'] = daily_ohlc['parkinson_vol'].rolling(5, min_periods=2).mean()

# Rolling realized vol (5-day)
daily_ohlc['realized_vol_5d'] = daily_ohlc['log_return'].rolling(5, min_periods=2).std()

daily_ohlc.dropna(subset=['log_return', 'parkinson_vol_5d', 'realized_vol_5d'], inplace=True)
daily_ohlc.reset_index(drop=True, inplace=True)

print(f"  Daily bars: {len(daily_ohlc)}")

# =============================================================================
# --- PHASE 3: WALK-FORWARD HMM REGIME DETECTION ---
# =============================================================================
print("\nPHASE 3: Walk-Forward HMM regime detection...")

# HMM observation features: [log_return, range_pct, parkinson_vol_5d]
obs_cols = ['log_return', 'range_pct', 'parkinson_vol_5d']

daily_ohlc['hmm_regime'] = np.nan
daily_ohlc['year'] = daily_ohlc['date'].dt.year
years = sorted(daily_ohlc['year'].unique())

# We need at least HMM_LOOKBACK_DAYS before we start predicting
# Walk-forward: fit HMM on past data, predict regime for current year
for yr in years:
    yr_mask = daily_ohlc['year'] == yr
    yr_indices = daily_ohlc[yr_mask].index

    if len(yr_indices) == 0:
        continue

    # Training data: all data before this year, up to HMM_LOOKBACK_DAYS
    train_end_idx = yr_indices[0]
    train_start_idx = max(0, train_end_idx - HMM_LOOKBACK_DAYS)

    if train_end_idx - train_start_idx < 100:
        # Not enough training data, skip
        continue

    X_train = daily_ohlc.loc[train_start_idx:train_end_idx - 1, obs_cols].values
    X_test  = daily_ohlc.loc[yr_indices, obs_cols].values

    try:
        hmm = GaussianHMM(
            n_components=N_REGIMES,
            covariance_type='full',
            n_iter=200,
            random_state=42,
            tol=1e-4,
        )
        hmm.fit(X_train)

        # Predict regimes for test year
        regimes_test = hmm.predict(X_test)

        # Also predict on training set to establish regime-volatility mapping
        regimes_train = hmm.predict(X_train)

        # Map regime indices to ordered volatility labels:
        # Sort regimes by their mean absolute return (proxy for volatility)
        train_df_tmp = pd.DataFrame({
            'regime': regimes_train,
            'abs_ret': np.abs(X_train[:, 0]),  # log_return column
        })
        regime_vol = train_df_tmp.groupby('regime')['abs_ret'].mean().sort_values()
        # regime_vol index: [lowest_vol_regime, mid, highest_vol_regime]
        vol_order = {regime_idx: rank for rank, regime_idx in enumerate(regime_vol.index)}
        # 0 = Low Vol, 1 = Medium Vol, 2 = High Vol

        mapped_regimes = np.array([vol_order[r] for r in regimes_test])
        daily_ohlc.loc[yr_indices, 'hmm_regime'] = mapped_regimes

        regime_counts = pd.Series(mapped_regimes).value_counts().sort_index()
        print(f"  {yr}: {len(X_test)} days | "
              f"Low={regime_counts.get(0, 0)} Med={regime_counts.get(1, 0)} High={regime_counts.get(2, 0)}")

    except Exception as e:
        print(f"  {yr}: HMM fit failed: {e}")
        continue

# Shift regime by 1 day: use YESTERDAY's regime for today's trade decision (no look-ahead)
daily_ohlc['regime_for_trading'] = daily_ohlc['hmm_regime'].shift(1)

regime_labels = {0: 'Low Vol', 1: 'Med Vol', 2: 'High Vol'}
daily_ohlc['regime_label'] = daily_ohlc['regime_for_trading'].map(regime_labels)

valid_regime = daily_ohlc.dropna(subset=['regime_for_trading'])
print(f"\n  Days with valid regime labels: {len(valid_regime)}")

# Build lookup: date -> regime
regime_lookup = dict(zip(
    daily_ohlc['date'].dt.date,
    daily_ohlc['regime_for_trading']
))

# =============================================================================
# --- PHASE 4: BACKTEST ENGINE ---
# =============================================================================
print("\nPHASE 4: Running backtest with regime labels...")

dates = sorted(df_1m['date'].unique())
all_trades = []

for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')
    try:
        day_data = df_1m.loc[day_str]
    except KeyError:
        continue
    if day_data.empty:
        continue

    regime_val = regime_lookup.get(trade_date, np.nan)

    orb_end_dt = pd.Timestamp(f"{day_str} 09:30:00", tz='US/Eastern') + pd.Timedelta(minutes=ORB_MIN)
    orb_end_time = orb_end_dt.time()

    # ORB bars
    orb_mask = (day_data['time'] >= time(9, 30)) & (day_data['time'] < orb_end_time)
    orb_bars = day_data[orb_mask]
    if orb_bars.empty or len(orb_bars) < 3:
        continue

    orbH = orb_bars['high'].max()
    orbL = orb_bars['low'].min()
    orbRange = orbH - orbL
    if orbRange <= 0:
        continue

    # Entry scan
    entry_window = day_data[
        (day_data['time'] >= orb_end_time) & (day_data['time'] <= SESSION_ENTRY_CUTOFF)
    ]
    if entry_window.empty:
        continue

    has_traded = False
    pending_long = False
    pending_short = False
    entry_price = 0.0
    entry_time = None
    entry_dir = None
    sl_price = 0.0

    for idx, row in entry_window.iterrows():
        if has_traded:
            break
        was_pl = pending_long
        was_ps = pending_short

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
                entry_time = idx
                entry_dir = 'Long'
                has_traded = True
        elif was_ps:
            sl_price = orbH
            if vwap_val < sl_price and row['high'] >= vwap_val:
                entry_price = vwap_val if vwap_val >= row['low'] else row['low']
                entry_time = idx
                entry_dir = 'Short'
                has_traded = True

    if not has_traded:
        continue

    # Exit scan
    try:
        exit_idx_pos = day_data.index.get_loc(entry_time) + 1
        exit_path = day_data.iloc[exit_idx_pos:] if exit_idx_pos < len(day_data) else pd.DataFrame()
    except Exception:
        exit_path = pd.DataFrame()

    for tp_size in TP_SIZES:
        tp_price = (orbH + orbRange * tp_size) if entry_dir == 'Long' else (orbL - orbRange * tp_size)
        exit_price_val = None
        exit_time_val = None
        exit_reason = "EOD"

        for e_idx, e_row in exit_path.iterrows():
            if e_row['time'] >= SESSION_FORCE_EXIT:
                exit_price_val = e_row['close']
                exit_time_val = e_idx
                exit_reason = "TimeClose"
                break
            if entry_dir == 'Long':
                if e_row['low'] <= sl_price:
                    exit_price_val = sl_price; exit_time_val = e_idx; exit_reason = "SL"; break
                elif e_row['high'] >= tp_price:
                    exit_price_val = tp_price; exit_time_val = e_idx; exit_reason = "TP"; break
            else:
                if e_row['high'] >= sl_price:
                    exit_price_val = sl_price; exit_time_val = e_idx; exit_reason = "SL"; break
                elif e_row['low'] <= tp_price:
                    exit_price_val = tp_price; exit_time_val = e_idx; exit_reason = "TP"; break

        if exit_time_val is None:
            exit_price_val = exit_path.iloc[-1]['close'] if not exit_path.empty else entry_price
            exit_reason = "EOD"

        pnl = (exit_price_val - entry_price) if entry_dir == 'Long' else (entry_price - exit_price_val)

        all_trades.append({
            'date': trade_date,
            'tp_size': tp_size,
            'direction': entry_dir,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'orbRange': orbRange,
            'regime': regime_val,
            'regime_label': regime_labels.get(regime_val, 'Unknown'),
        })

trade_df = pd.DataFrame(all_trades)
trade_df['date'] = pd.to_datetime(trade_df['date'])

# Remove trades without regime labels
trade_with_regime = trade_df.dropna(subset=['regime']).copy()
trade_with_regime['regime'] = trade_with_regime['regime'].astype(int)

print(f"  Total trades: {len(trade_df)}")
print(f"  Trades with regime labels: {len(trade_with_regime)}")

# =============================================================================
# --- PHASE 5: PERFORMANCE ANALYSIS BY REGIME ---
# =============================================================================
print("\nPHASE 5: Analyzing performance by regime...")

def calc_stats(pnl_series, label=""):
    n = len(pnl_series)
    if n == 0:
        return {'Label': label, 'Trades': 0, 'WinRate': 0, 'TotalPnL': 0,
                'AvgPnL': 0, 'Sharpe': 0, 'MaxDrawdown': 0, 'ProfitFactor': 0}
    wins = (pnl_series > 0).sum()
    total = pnl_series.sum()
    wr = wins / n
    avg = pnl_series.mean()
    std = pnl_series.std() if n > 1 else 1
    sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
    cum = pnl_series.cumsum()
    max_dd = (cum - cum.cummax()).min()
    gross_profit = pnl_series[pnl_series > 0].sum()
    gross_loss = abs(pnl_series[pnl_series < 0].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else np.inf
    return {'Label': label, 'Trades': n, 'WinRate': wr, 'TotalPnL': total,
            'AvgPnL': avg, 'Sharpe': sharpe, 'MaxDrawdown': max_dd, 'ProfitFactor': pf}

comparison_rows = []
equity_curves = {}

for tp_size in TP_SIZES:
    tp_trades = trade_with_regime[trade_with_regime['tp_size'] == tp_size].sort_values('date')

    # Baseline (all regimes)
    stats = calc_stats(tp_trades['pnl'].reset_index(drop=True), f"All Regimes TP={tp_size}")
    stats['TP_Size'] = tp_size
    stats['Regime'] = 'All'
    comparison_rows.append(stats)

    if tp_size == 1.0:
        equity_curves['All Regimes'] = tp_trades[['date', 'pnl']].copy()
        equity_curves['All Regimes']['cum_pnl'] = tp_trades['pnl'].cumsum().values

    # Per regime
    for reg_val in sorted(tp_trades['regime'].unique()):
        reg_name = regime_labels.get(reg_val, f'Regime {reg_val}')
        reg_trades = tp_trades[tp_trades['regime'] == reg_val].sort_values('date')
        stats = calc_stats(reg_trades['pnl'].reset_index(drop=True), f"{reg_name} TP={tp_size}")
        stats['TP_Size'] = tp_size
        stats['Regime'] = reg_name
        comparison_rows.append(stats)

        if tp_size == 1.0:
            eq = reg_trades[['date', 'pnl']].copy()
            eq['cum_pnl'] = reg_trades['pnl'].cumsum().values
            equity_curves[reg_name] = eq

    # Filtered: exclude High Vol
    filt = tp_trades[tp_trades['regime'] != 2].sort_values('date')
    stats = calc_stats(filt['pnl'].reset_index(drop=True), f"No HighVol TP={tp_size}")
    stats['TP_Size'] = tp_size
    stats['Regime'] = 'Exclude High Vol'
    comparison_rows.append(stats)

    if tp_size == 1.0:
        eq = filt[['date', 'pnl']].copy()
        eq['cum_pnl'] = filt['pnl'].cumsum().values
        equity_curves['Exclude High Vol'] = eq

    # Filtered: only Low Vol
    low_vol = tp_trades[tp_trades['regime'] == 0].sort_values('date')
    stats = calc_stats(low_vol['pnl'].reset_index(drop=True), f"Low Vol Only TP={tp_size}")
    stats['TP_Size'] = tp_size
    stats['Regime'] = 'Low Vol Only'
    comparison_rows.append(stats)

    if tp_size == 1.0:
        eq = low_vol[['date', 'pnl']].copy()
        eq['cum_pnl'] = low_vol['pnl'].cumsum().values
        equity_curves['Low Vol Only'] = eq

compare_df = pd.DataFrame(comparison_rows)
compare_df.to_csv(os.path.join(OUTPUT_DIR, 'regime_performance_compare.csv'), index=False)
trade_with_regime.to_csv(os.path.join(OUTPUT_DIR, 'regime_raw_trades.csv'), index=False)

# Save regime time-series
daily_ohlc[['date', 'hmm_regime', 'regime_for_trading', 'regime_label',
            'log_return', 'parkinson_vol_5d', 'realized_vol_5d']].to_csv(
    os.path.join(OUTPUT_DIR, 'regime_daily_labels.csv'), index=False)

print("  CSVs saved.")

# Print summary
tp1 = compare_df[compare_df['TP_Size'] == 1.0]
for _, r in tp1.iterrows():
    print(f"  {r['Regime']:20s} | Trades={int(r['Trades']):5d} | "
          f"WR={r['WinRate']:.2%} | PnL={r['TotalPnL']:8.1f} | "
          f"Sharpe={r['Sharpe']:.3f} | MaxDD={r['MaxDrawdown']:.1f}")

# =============================================================================
# --- PHASE 6: PLOTLY HTML DASHBOARD ---
# =============================================================================
print("\nPHASE 6: Generating Markov Regime Dashboard...")

DARK_BG  = "#0f1117"
CARD_BG  = "#1a1d27"
ACCENT   = "#7c6fff"
GREEN    = "#22d3a0"
RED_CLR  = "#f87171"
GOLD     = "#fbbf24"
BLUE_CLR = "#38bdf8"
ORANGE   = "#fb923c"
TEXT_CLR = "#e2e8f0"
REGIME_COLORS = {0: GREEN, 1: GOLD, 2: RED_CLR}
REGIME_ORDER = ['Low Vol', 'Med Vol', 'High Vol']

# --- Fig 1: Regime Timeline ---
regime_ts = daily_ohlc.dropna(subset=['hmm_regime']).copy()
regime_ts['color'] = regime_ts['hmm_regime'].map(REGIME_COLORS)

fig_timeline = go.Figure()
fig_timeline.add_trace(go.Scatter(
    x=regime_ts['date'], y=regime_ts['daily_close'],
    mode='lines', line=dict(color='#555', width=1),
    name='NQ Close', showlegend=True,
))

for reg_val, reg_name in regime_labels.items():
    reg_data = regime_ts[regime_ts['hmm_regime'] == reg_val]
    fig_timeline.add_trace(go.Scatter(
        x=reg_data['date'], y=reg_data['daily_close'],
        mode='markers',
        marker=dict(color=REGIME_COLORS[reg_val], size=3, opacity=0.7),
        name=reg_name,
    ))

fig_timeline.update_layout(
    title="NQ Close Price with Markov Volatility Regime Overlay",
    xaxis_title="Date", yaxis_title="NQ Close",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"),
    height=420,
)

# --- Fig 2: Equity Curves by Regime Filter ---
fig_eq = go.Figure()
palette = {'All Regimes': '#555', 'Low Vol': GREEN, 'Med Vol': GOLD,
           'High Vol': RED_CLR, 'Exclude High Vol': BLUE_CLR, 'Low Vol Only': ACCENT}

for label, eq_data in equity_curves.items():
    fig_eq.add_trace(go.Scatter(
        x=eq_data['date'], y=eq_data['cum_pnl'],
        mode='lines', name=label,
        line=dict(color=palette.get(label, ORANGE),
                  width=2.5 if label in ['All Regimes', 'Exclude High Vol'] else 1.5,
                  dash='dot' if label == 'All Regimes' else 'solid'),
    ))

fig_eq.update_layout(
    title="Equity Curves by Regime Filter (TP=1.0R)",
    xaxis_title="Date", yaxis_title="Cumulative PnL (points)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"),
    height=450,
)

# --- Fig 3: Per-Regime Performance Bars (TP=1.0) ---
tp1_regimes = compare_df[
    (compare_df['TP_Size'] == 1.0) &
    (compare_df['Regime'].isin(REGIME_ORDER + ['All', 'Exclude High Vol', 'Low Vol Only']))
].copy()

metrics = ['WinRate', 'TotalPnL', 'Sharpe', 'MaxDrawdown', 'ProfitFactor', 'Trades']
fig_bars = make_subplots(rows=2, cols=3, subplot_titles=metrics,
                         vertical_spacing=0.18, horizontal_spacing=0.10)

bar_colors = {
    'Low Vol': GREEN, 'Med Vol': GOLD, 'High Vol': RED_CLR,
    'All': '#555', 'Exclude High Vol': BLUE_CLR, 'Low Vol Only': ACCENT,
}

for idx, metric in enumerate(metrics):
    row_i = idx // 3 + 1
    col_i = idx % 3 + 1
    for _, r in tp1_regimes.iterrows():
        fig_bars.add_trace(go.Bar(
            x=[r['Regime']], y=[r[metric]],
            name=r['Regime'],
            marker_color=bar_colors.get(r['Regime'], ORANGE),
            showlegend=(idx == 0),
            text=[f"{r[metric]:.3f}" if metric != 'Trades' else f"{int(r[metric])}"],
            textposition='outside', textfont=dict(size=10),
        ), row=row_i, col=col_i)

fig_bars.update_layout(
    title="Performance Metrics by Regime (TP=1.0R)",
    barmode='group',
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"),
    height=580,
    showlegend=False,
)
for ann in fig_bars.layout.annotations:
    ann.font.color = TEXT_CLR

# --- Fig 4: Volatility distribution by regime ---
fig_vol = go.Figure()
for reg_val, reg_name in regime_labels.items():
    reg_data = regime_ts[regime_ts['hmm_regime'] == reg_val]
    fig_vol.add_trace(go.Histogram(
        x=reg_data['parkinson_vol_5d'] * 100,
        name=reg_name, marker_color=REGIME_COLORS[reg_val],
        opacity=0.70, nbinsx=30,
    ))
fig_vol.update_layout(
    barmode='overlay',
    title="Parkinson Volatility Distribution by Regime",
    xaxis_title="5-Day Parkinson Vol (%)", yaxis_title="Days",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG),
    height=380,
)

# --- Fig 5: Regime Transition Matrix Heatmap ---
regime_seq = daily_ohlc.dropna(subset=['hmm_regime'])['hmm_regime'].astype(int).values
trans_matrix = np.zeros((N_REGIMES, N_REGIMES))
for i in range(len(regime_seq) - 1):
    trans_matrix[regime_seq[i], regime_seq[i + 1]] += 1
# Normalize rows
row_sums = trans_matrix.sum(axis=1, keepdims=True)
trans_matrix_pct = trans_matrix / np.where(row_sums > 0, row_sums, 1)

fig_trans = go.Figure(go.Heatmap(
    z=trans_matrix_pct,
    x=[regime_labels[i] for i in range(N_REGIMES)],
    y=[regime_labels[i] for i in range(N_REGIMES)],
    colorscale='Viridis',
    text=np.round(trans_matrix_pct, 3),
    texttemplate="%{text:.1%}",
    textfont=dict(size=14),
    showscale=True,
))
fig_trans.update_layout(
    title="Regime Transition Probability Matrix",
    xaxis_title="To Regime", yaxis_title="From Regime",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    height=400,
    yaxis=dict(autorange='reversed'),
)

# --- Fig 6: ORB Range distribution by Regime ---
tp1_trades = trade_with_regime[trade_with_regime['tp_size'] == 1.0]
fig_orb_range = go.Figure()
for reg_val in sorted(tp1_trades['regime'].unique()):
    reg_name = regime_labels.get(reg_val, f'Regime {reg_val}')
    reg_t = tp1_trades[tp1_trades['regime'] == reg_val]
    fig_orb_range.add_trace(go.Box(
        y=reg_t['orbRange'], name=reg_name,
        marker_color=REGIME_COLORS.get(reg_val, ORANGE),
        boxmean=True,
    ))
fig_orb_range.update_layout(
    title="ORB Range Distribution by Regime",
    yaxis_title="ORB Range (points)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    height=400,
)

# =============================================================================
# --- ASSEMBLE HTML ---
# =============================================================================
def section(title, subtitle=""):
    sub_html = f"<p style='color:#94a3b8;margin:4px 0 12px;font-size:14px'>{subtitle}</p>" if subtitle else ""
    return f"""
    <div style='background:{CARD_BG};border-radius:12px;padding:28px 32px;margin:20px 0;
                border:1px solid #2a2d3a;box-shadow:0 4px 24px rgba(0,0,0,0.4)'>
        <h2 style='margin:0 0 6px;color:{ACCENT};font-size:18px;letter-spacing:.5px'>{title}</h2>
        {sub_html}
    """

# KPI
tp1_all  = tp1_regimes[tp1_regimes['Regime'] == 'All'].iloc[0]
tp1_excl = tp1_regimes[tp1_regimes['Regime'] == 'Exclude High Vol'].iloc[0]
tp1_low  = tp1_regimes[tp1_regimes['Regime'] == 'Low Vol Only'].iloc[0]

html_parts = [f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ORB Markov Regime Filter</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: {DARK_BG}; color: {TEXT_CLR};
      min-height: 100vh; padding: 0 0 60px;
    }}
    .hero {{
      background: linear-gradient(135deg,#1a1d27 0%,#12151f 60%,#0f1117 100%);
      border-bottom: 1px solid #1e2130; padding: 48px 40px 36px;
    }}
    .hero h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
    .hero p  {{ color: #94a3b8; font-size: 15px; max-width: 720px; }}
    .badge {{ display:inline-block; padding:3px 10px; border-radius:99px;
              font-size:12px; font-weight:600; margin-left:10px; vertical-align:middle; }}
    .badge-green {{ background:#0d3327; color:{GREEN}; }}
    .kpi-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px; margin: 20px 0;
    }}
    .kpi {{
      background: #12151f; border-radius: 10px; padding: 18px 20px;
      border: 1px solid #1e2130;
    }}
    .kpi .val {{ font-size: 24px; font-weight: 700; }}
    .kpi .lbl {{ font-size: 11px; color: #6b7280; margin-top: 4px; }}
    .kpi.green .val {{ color: {GREEN}; }}
    .kpi.red   .val {{ color: {RED_CLR}; }}
    .kpi.gold  .val {{ color: {GOLD}; }}
    .kpi.blue  .val {{ color: {ACCENT}; }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 0 32px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }}
    th {{ background: #12151f; color: {ACCENT}; padding: 10px 14px; text-align: left;
          border-bottom: 2px solid #1e2130; }}
    td {{ padding: 9px 14px; border-bottom: 1px solid #1e2130; color: {TEXT_CLR}; }}
    tr:hover td {{ background: #12151f; }}
    .pos {{ color: {GREEN}; font-weight: 600; }}
    .neg {{ color: {RED_CLR}; font-weight: 600; }}
    .twocol {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    @media (max-width: 900px) {{ .twocol {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<div class="hero">
  <div class="container">
    <h1>ORB + VWAP Retest -- Markov Regime Filter
      <span class="badge badge-green">HMM {N_REGIMES}-State</span>
    </h1>
    <p>Hidden Markov Model (Gaussian HMM) on [log return, range %, Parkinson vol]
       identifies Low / Medium / High volatility regimes. Trades are filtered by
       yesterday's regime to avoid look-ahead bias.</p>
  </div>
</div>
<div class="container">
"""]

# KPI grid
def kpi_cls(val, threshold=0):
    return 'green' if val > threshold else 'red'

html_parts.append(f"""
{section("Key Metrics (TP=1.0R)", "Comparing All Regimes vs Regime-Filtered")}
<div class="kpi-grid">
  <div class="kpi"><div class="val" style="color:#888">{int(tp1_all['Trades'])}</div>
    <div class="lbl">All: Trades</div></div>
  <div class="kpi {kpi_cls(tp1_all['WinRate'], 0.45)}"><div class="val">{tp1_all['WinRate']:.1%}</div>
    <div class="lbl">All: Win Rate</div></div>
  <div class="kpi {kpi_cls(tp1_all['TotalPnL'])}"><div class="val">{tp1_all['TotalPnL']:.0f}</div>
    <div class="lbl">All: Total PnL</div></div>
  <div class="kpi gold"><div class="val">{tp1_all['Sharpe']:.3f}</div>
    <div class="lbl">All: Sharpe</div></div>

  <div class="kpi blue"><div class="val">{int(tp1_excl['Trades'])}</div>
    <div class="lbl">Excl High Vol: Trades</div></div>
  <div class="kpi {kpi_cls(tp1_excl['WinRate'], 0.45)}"><div class="val">{tp1_excl['WinRate']:.1%}</div>
    <div class="lbl">Excl High Vol: WR</div></div>
  <div class="kpi {kpi_cls(tp1_excl['TotalPnL'])}"><div class="val">{tp1_excl['TotalPnL']:.0f}</div>
    <div class="lbl">Excl High Vol: PnL</div></div>
  <div class="kpi gold"><div class="val">{tp1_excl['Sharpe']:.3f}</div>
    <div class="lbl">Excl High Vol: Sharpe</div></div>

  <div class="kpi blue"><div class="val">{int(tp1_low['Trades'])}</div>
    <div class="lbl">Low Vol Only: Trades</div></div>
  <div class="kpi {kpi_cls(tp1_low['WinRate'], 0.45)}"><div class="val">{tp1_low['WinRate']:.1%}</div>
    <div class="lbl">Low Vol Only: WR</div></div>
  <div class="kpi {kpi_cls(tp1_low['TotalPnL'])}"><div class="val">{tp1_low['TotalPnL']:.0f}</div>
    <div class="lbl">Low Vol Only: PnL</div></div>
  <div class="kpi gold"><div class="val">{tp1_low['Sharpe']:.3f}</div>
    <div class="lbl">Low Vol Only: Sharpe</div></div>
</div></div>
""")

# Charts
for fig_obj in [fig_eq, fig_timeline, fig_bars, fig_vol]:
    html_parts.append(f"<div style='margin:20px 0'>{fig_obj.to_html(full_html=False, include_plotlyjs='cdn')}</div>")

# Two-column: Transition Matrix + ORB Range Box
html_parts.append(f"""<div class="twocol">
  <div>{fig_trans.to_html(full_html=False, include_plotlyjs='cdn')}</div>
  <div>{fig_orb_range.to_html(full_html=False, include_plotlyjs='cdn')}</div>
</div>""")

# Full comparison table
html_parts.append(f"""
{section("Full Performance Table", "All TP Sizes x Regime Filters")}
<table>
<thead><tr>
  <th>TP</th><th>Regime</th><th>Trades</th><th>Win Rate</th>
  <th>Total PnL</th><th>Avg PnL</th><th>Sharpe</th><th>Max DD</th><th>PF</th>
</tr></thead><tbody>
""")
for _, r in compare_df.sort_values(['TP_Size', 'Regime']).iterrows():
    pnl_cls = 'pos' if r['TotalPnL'] > 0 else 'neg'
    html_parts.append(f"""<tr>
      <td>{r['TP_Size']}</td><td>{r['Regime']}</td><td>{int(r['Trades'])}</td>
      <td>{r['WinRate']:.2%}</td>
      <td class="{pnl_cls}">{r['TotalPnL']:.2f}</td>
      <td>{r['AvgPnL']:.3f}</td><td>{r['Sharpe']:.3f}</td>
      <td class="neg">{r['MaxDrawdown']:.2f}</td>
      <td>{r['ProfitFactor']:.3f}</td></tr>""")

html_parts.append("</tbody></table></div>")
html_parts.append("</div></body></html>")

out_html = os.path.join(OUTPUT_DIR, 'markov_regime_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write('\n'.join(html_parts))

print(f"\n{'='*60}")
print("DONE. Outputs:")
print(f"  Dashboard     : {out_html}")
print(f"  Raw trades    : {os.path.join(OUTPUT_DIR, 'regime_raw_trades.csv')}")
print(f"  Performance   : {os.path.join(OUTPUT_DIR, 'regime_performance_compare.csv')}")
print(f"  Regime labels : {os.path.join(OUTPUT_DIR, 'regime_daily_labels.csv')}")
print("=" * 60)
