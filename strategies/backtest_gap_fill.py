"""
NQ Opening Auction Gap Fill Backtest
=====================================
逢開盤跳空（相對前日 RTH 收盤）做反向回補交易。
- Gap Up (Open > Prev RTH Close) → Short，目標回補前日收盤
- Gap Down (Open < Prev RTH Close) → Long，目標回補前日收盤
- 測試不同回補目標（25% / 50% / 75% / 100%）及最小 Gap 門檻

Dependencies: databento, pandas, numpy, plotly
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

warnings.filterwarnings('ignore')

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================
FILE_PATH = r"C:\Users\user\Downloads\NQ 1m data\NQ20100606-20251212.ohlcv-1m.dbn"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\backtest_results\gap_fill"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Strategy parameters
MIN_GAP_POINTS   = [5, 10, 15, 20, 30]    # 最小缺口點數門檻（NQ points）
FILL_TARGETS     = [0.25, 0.50, 0.75, 1.00]  # 回補比例目標
ENTRY_DELAY_BARS = 1           # 開盤後等幾根 1m bar 才進場（避免開盤瞬間混亂）
SESSION_RTH_OPEN  = time(9, 30)
SESSION_RTH_CLOSE = time(16, 0)
SESSION_FORCE_EXIT = time(15, 55)    # 最晚出場時間
ENTRY_CUTOFF      = time(11, 0)      # 超過此時間不進新倉（缺口通常前2h填完）

# Stop loss: 缺口額外延伸的容忍點數
STOP_EXTENSION_POINTS = [5, 10, 15, 20]  # 原始缺口大小 + 此值 = SL 位置

pio.templates.default = "plotly_dark"

# =============================================================================
# --- PHASE 1: DATA LOADING ---
# =============================================================================
print("=" * 60)
print("PHASE 1: Loading data...")
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

# =============================================================================
# --- PHASE 2: COMPUTE DAILY GAP ---
# =============================================================================
print("\nPHASE 2: Computing daily gaps...")

# Previous RTH Close = last bar of RTH session (close to 16:00)
rth_bars = df_1m[(df_1m.index.time >= SESSION_RTH_OPEN) &
                 (df_1m.index.time < SESSION_RTH_CLOSE)].copy()

prev_rth_close = (
    rth_bars.groupby('date')['close']
    .last()
    .reset_index()
    .rename(columns={'close': 'prev_rth_close'})
)
prev_rth_close['next_date_close'] = prev_rth_close['prev_rth_close'].shift(0)
prev_rth_close['prev_rth_close'] = prev_rth_close['prev_rth_close'].shift(1)
# Now prev_rth_close['prev_rth_close'] is the PREVIOUS day's RTH close

# Today's RTH Open = first bar at exactly 09:30
rth_open = (
    df_1m[df_1m.index.time == SESSION_RTH_OPEN]
    .groupby('date')['open']
    .first()
    .reset_index()
    .rename(columns={'open': 'rth_open'})
)

# Also get previous day's RTH High/Low for context
prev_rth_hl = (
    rth_bars.groupby('date').agg(
        rth_high=('high', 'max'),
        rth_low=('low', 'min'),
        rth_close=('close', 'last'),
        rth_volume=('volume', 'sum'),
    )
    .reset_index()
)
prev_rth_hl['prev_high']   = prev_rth_hl['rth_high'].shift(1)
prev_rth_hl['prev_low']    = prev_rth_hl['rth_low'].shift(1)
prev_rth_hl['prev_volume'] = prev_rth_hl['rth_volume'].shift(1)

# ATR for normalisation
prev_rth_hl['tr'] = np.maximum(
    prev_rth_hl['rth_high'] - prev_rth_hl['rth_low'],
    np.maximum(
        (prev_rth_hl['rth_high'] - prev_rth_hl['rth_close'].shift(1)).abs(),
        (prev_rth_hl['rth_low']  - prev_rth_hl['rth_close'].shift(1)).abs(),
    )
)
prev_rth_hl['atr_14'] = prev_rth_hl['tr'].rolling(14, min_periods=3).mean()

# Merge all
daily_info = (
    prev_rth_close[['date', 'prev_rth_close']]
    .merge(rth_open, on='date', how='inner')
    .merge(prev_rth_hl[['date', 'prev_high', 'prev_low', 'atr_14', 'rth_high', 'rth_low']], on='date', how='left')
)

daily_info['gap_points']  = daily_info['rth_open'] - daily_info['prev_rth_close']
daily_info['gap_pct']     = daily_info['gap_points'] / daily_info['prev_rth_close'] * 100
daily_info['gap_dir']     = np.sign(daily_info['gap_points'])  # +1=gap up, -1=gap down
daily_info['gap_abs']     = daily_info['gap_points'].abs()
daily_info['gap_vs_atr']  = daily_info['gap_abs'] / daily_info['atr_14']

daily_info.dropna(subset=['prev_rth_close', 'rth_open', 'gap_points'], inplace=True)

print(f"  Total days with gap data: {len(daily_info)}")
print(f"  Gap Up:   {(daily_info['gap_dir'] > 0).sum()} days")
print(f"  Gap Down: {(daily_info['gap_dir'] < 0).sum()} days")
print(f"  Zero Gap: {(daily_info['gap_dir'] == 0).sum()} days")
print(f"  Avg Gap:  {daily_info['gap_abs'].mean():.1f} pts")
print(f"  Median Gap: {daily_info['gap_abs'].median():.1f} pts")

gap_lookup = daily_info.set_index('date').to_dict('index')

# =============================================================================
# --- PHASE 3: BACKTEST ENGINE ---
# =============================================================================
print("\nPHASE 3: Running Gap Fill backtest...")

dates = sorted(df_1m['date'].unique())
all_trades = []

for trade_date in dates:
    day_str = trade_date.strftime('%Y-%m-%d')

    if trade_date not in gap_lookup:
        continue

    info          = gap_lookup[trade_date]
    gap_points    = info['gap_points']
    gap_abs       = info['gap_abs']
    gap_dir       = info['gap_dir']
    rth_open_px   = info['rth_open']
    prev_close_px = info['prev_rth_close']
    atr_14        = info['atr_14']

    # No gap or zero direction, skip
    if gap_dir == 0 or np.isnan(gap_points):
        continue

    try:
        day_data = df_1m.loc[day_str]
    except KeyError:
        continue
    if day_data.empty:
        continue

    # RTH bars only
    rth_day = day_data[(day_data['time'] >= SESSION_RTH_OPEN) &
                       (day_data['time'] < SESSION_FORCE_EXIT)]
    if len(rth_day) < 5:
        continue

    # Entry: after ENTRY_DELAY_BARS bars from open
    entry_bar_idx = ENTRY_DELAY_BARS  # 0-indexed into rth_day
    if entry_bar_idx >= len(rth_day):
        continue

    entry_bar  = rth_day.iloc[entry_bar_idx]
    entry_time = rth_day.index[entry_bar_idx]

    # Skip if entry is after cutoff
    if entry_time.time() > ENTRY_CUTOFF:
        continue

    # Entry price = open of the bar after delay
    entry_price = entry_bar['open']

    # Direction: fade the gap
    # Gap Up  → Short (expect fill back down to prev_close)
    # Gap Down → Long  (expect fill back up to prev_close)
    entry_dir = 'Short' if gap_dir > 0 else 'Long'

    # Exit path: bars AFTER entry bar
    exit_path = rth_day.iloc[entry_bar_idx + 1:]

    for sl_ext in STOP_EXTENSION_POINTS:
        # SL: if gap EXTENDS further than entry by sl_ext points
        if entry_dir == 'Short':
            sl_price = entry_price + sl_ext          # gap up short: SL above entry
        else:
            sl_price = entry_price - sl_ext          # gap down long: SL below entry

        for fill_pct in FILL_TARGETS:
            # Target: fill fill_pct of gap toward prev_close
            fill_target = entry_price + (-gap_dir) * gap_abs * fill_pct
            # For Short: fill_target = entry_price - gap_abs * fill_pct (moving toward prev_close)
            # For Long:  fill_target = entry_price + gap_abs * fill_pct

            exit_price_val = None
            exit_time_val  = None
            exit_reason    = "EOD"

            for e_idx, e_row in exit_path.iterrows():
                if e_row['time'] >= SESSION_FORCE_EXIT:
                    exit_price_val = e_row['close']
                    exit_time_val  = e_idx
                    exit_reason    = "TimeClose"
                    break

                if entry_dir == 'Short':
                    # SL: price goes higher (gap extends)
                    if e_row['high'] >= sl_price:
                        exit_price_val = sl_price
                        exit_time_val  = e_idx
                        exit_reason    = "SL"
                        break
                    # TP: price fills back toward prev close
                    if e_row['low'] <= fill_target:
                        exit_price_val = fill_target
                        exit_time_val  = e_idx
                        exit_reason    = "TP"
                        break
                else:  # Long
                    # SL: price goes lower (gap extends)
                    if e_row['low'] <= sl_price:
                        exit_price_val = sl_price
                        exit_time_val  = e_idx
                        exit_reason    = "SL"
                        break
                    # TP: price fills back toward prev close
                    if e_row['high'] >= fill_target:
                        exit_price_val = fill_target
                        exit_time_val  = e_idx
                        exit_reason    = "TP"
                        break

            if exit_time_val is None:
                exit_price_val = exit_path.iloc[-1]['close'] if not exit_path.empty else entry_price
                exit_reason    = "EOD"

            pnl = (entry_price - exit_price_val) if entry_dir == 'Short' else (exit_price_val - entry_price)

            all_trades.append({
                'date'        : trade_date,
                'direction'   : entry_dir,
                'gap_points'  : gap_points,
                'gap_abs'     : gap_abs,
                'gap_pct'     : info['gap_pct'],
                'gap_vs_atr'  : info['gap_vs_atr'],
                'entry_price' : entry_price,
                'fill_target' : fill_pct,
                'sl_ext'      : sl_ext,
                'exit_reason' : exit_reason,
                'pnl'         : pnl,
            })

trade_df = pd.DataFrame(all_trades)
print(f"  Total trade records: {len(trade_df)}")

# =============================================================================
# --- PHASE 4: PERFORMANCE ANALYSIS ---
# =============================================================================
print("\nPHASE 4: Performance analysis...")

def calc_stats(pnl_series, label=""):
    n = len(pnl_series)
    if n == 0:
        return {'label': label, 'n': 0, 'wr': 0, 'total': 0,
                'avg': 0, 'sharpe': 0, 'maxdd': 0, 'pf': 0}
    wins = (pnl_series > 0).sum()
    total = pnl_series.sum()
    wr = wins / n
    avg = pnl_series.mean()
    std = pnl_series.std() if n > 1 else 1e-9
    sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
    cum = pnl_series.cumsum()
    maxdd = (cum - cum.cummax()).min()
    gp = pnl_series[pnl_series > 0].sum()
    gl = pnl_series[pnl_series < 0].abs().sum()
    pf = gp / gl if gl > 0 else np.inf
    return {'label': label, 'n': n, 'wr': wr, 'total': total,
            'avg': avg, 'sharpe': sharpe, 'maxdd': maxdd, 'pf': pf}

# --- Grid: fill_target × sl_ext ---
grid_rows = []
for fill_pct in FILL_TARGETS:
    for sl_ext in STOP_EXTENSION_POINTS:
        subset = trade_df[
            (trade_df['fill_target'] == fill_pct) &
            (trade_df['sl_ext'] == sl_ext)
        ]['pnl'].reset_index(drop=True)
        s = calc_stats(subset, f"Fill={fill_pct:.0%} SL+{sl_ext}")
        s['fill_target'] = fill_pct
        s['sl_ext'] = sl_ext
        grid_rows.append(s)
grid_df = pd.DataFrame(grid_rows)

# --- Gap size buckets ---
bucket_rows = []
best_cfg = grid_df.sort_values('sharpe', ascending=False).iloc[0]
best_fill = best_cfg['fill_target']
best_sl   = best_cfg['sl_ext']
best_trades = trade_df[
    (trade_df['fill_target'] == best_fill) &
    (trade_df['sl_ext'] == best_sl)
].copy()

for min_gap in MIN_GAP_POINTS:
    subset = best_trades[best_trades['gap_abs'] >= min_gap]['pnl'].reset_index(drop=True)
    s = calc_stats(subset, f"Gap>={min_gap}pts")
    s['min_gap'] = min_gap
    bucket_rows.append(s)
gap_df = pd.DataFrame(bucket_rows)

# --- Gap type breakdown ---
gap_type_rows = []
for gap_type, label in [(1, 'Gap Up (Short)'), (-1, 'Gap Down (Long)')]:
    subset = best_trades[best_trades['direction'] == ('Short' if gap_type > 0 else 'Long')]['pnl'].reset_index(drop=True)
    s = calc_stats(subset, label)
    s['gap_type'] = label
    gap_type_rows.append(s)
gap_type_df = pd.DataFrame(gap_type_rows)

# --- Yearly breakdown ---
best_trades['year'] = pd.to_datetime(best_trades['date']).dt.year
yearly_rows = []
for yr in sorted(best_trades['year'].unique()):
    subset = best_trades[best_trades['year'] == yr]['pnl'].reset_index(drop=True)
    s = calc_stats(subset, str(yr))
    s['year'] = yr
    yearly_rows.append(s)
yearly_df = pd.DataFrame(yearly_rows)

# Save CSVs
grid_df.to_csv(os.path.join(OUTPUT_DIR, 'gap_fill_grid.csv'), index=False)
best_trades.to_csv(os.path.join(OUTPUT_DIR, 'gap_fill_best_trades.csv'), index=False)
gap_df.to_csv(os.path.join(OUTPUT_DIR, 'gap_fill_by_size.csv'), index=False)
yearly_df.to_csv(os.path.join(OUTPUT_DIR, 'gap_fill_yearly.csv'), index=False)

print(f"\n  Best config: Fill={best_fill:.0%}, SL+{best_sl}pts")
print(f"  {'Label':<30} {'N':>6} {'WR':>8} {'PnL':>10} {'Sharpe':>8} {'MaxDD':>10} {'PF':>7}")
print("  " + "-"*75)
for row in [calc_stats(best_trades['pnl'].reset_index(drop=True), 'All Gaps')] + \
           [calc_stats(best_trades[best_trades['gap_abs'] >= g]['pnl'].reset_index(drop=True), f'Gap>={g}pts') for g in MIN_GAP_POINTS]:
    print(f"  {row['label']:<30} {int(row['n']):>6} {row['wr']:>8.2%} {row['total']:>10.1f} "
          f"{row['sharpe']:>8.3f} {row['maxdd']:>10.1f} {row['pf']:>7.3f}")

# =============================================================================
# --- PHASE 5: PLOTLY DASHBOARD ---
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

# --- Fig 1: Sharpe Heatmap (fill_target x sl_ext) ---
sharpe_pivot = grid_df.pivot(index='sl_ext', columns='fill_target', values='sharpe')
wr_pivot     = grid_df.pivot(index='sl_ext', columns='fill_target', values='wr')

fig_heat = make_subplots(rows=1, cols=2,
    subplot_titles=["Sharpe Ratio Grid", "Win Rate Grid"])

fig_heat.add_trace(go.Heatmap(
    z=sharpe_pivot.values,
    x=[f"Fill {v:.0%}" for v in sharpe_pivot.columns],
    y=[f"SL+{v}" for v in sharpe_pivot.index],
    colorscale='RdYlGn', text=np.round(sharpe_pivot.values, 3),
    texttemplate="%{text:.2f}", showscale=True, name='Sharpe',
), row=1, col=1)

fig_heat.add_trace(go.Heatmap(
    z=wr_pivot.values * 100,
    x=[f"Fill {v:.0%}" for v in wr_pivot.columns],
    y=[f"SL+{v}" for v in wr_pivot.index],
    colorscale='RdYlGn', text=np.round(wr_pivot.values * 100, 1),
    texttemplate="%{text:.1f}%", showscale=True, name='WinRate',
), row=1, col=2)

fig_heat.update_layout(
    title=f"Parameter Grid: Fill Target vs Stop Extension",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12), height=420,
)

# --- Fig 2: Equity Curve (best config, by gap size filter) ---
fig_eq = go.Figure()
palette = [ACCENT, GREEN, GOLD, RED_CLR, BLUE_CLR]
label_set = [('All Gaps', None)] + [(f'Gap>={g}pts', g) for g in MIN_GAP_POINTS]
for i, (lbl, min_gap) in enumerate(label_set):
    if min_gap is None:
        sub = best_trades.sort_values('date')
    else:
        sub = best_trades[best_trades['gap_abs'] >= min_gap].sort_values('date')
    if len(sub) < 5:
        continue
    fig_eq.add_trace(go.Scatter(
        x=pd.to_datetime(sub['date']), y=sub['pnl'].cumsum(),
        mode='lines', name=lbl,
        line=dict(color=palette[i % len(palette)],
                  width=2.5 if min_gap is None else 1.8,
                  dash='dot' if min_gap is None else 'solid'),
    ))
fig_eq.update_layout(
    title=f"Equity Curve by Minimum Gap Filter (Fill={best_fill:.0%}, SL+{best_sl}pts)",
    xaxis_title="Date", yaxis_title="Cumulative PnL (points)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13),
    legend=dict(bgcolor=CARD_BG, bordercolor="#333"), height=420,
)

# --- Fig 3: Annual Performance ---
colors_yearly = [GREEN if r > 0 else RED_CLR for r in yearly_df['total']]
fig_yr = make_subplots(rows=1, cols=2, subplot_titles=["Annual PnL", "Annual Sharpe"])
fig_yr.add_trace(go.Bar(x=yearly_df['year'], y=yearly_df['total'],
    marker_color=colors_yearly, text=yearly_df['total'].round(0),
    textposition='outside', name='PnL'), row=1, col=1)
fig_yr.add_trace(go.Bar(x=yearly_df['year'], y=yearly_df['sharpe'],
    marker_color=[GREEN if s > 0 else RED_CLR for s in yearly_df['sharpe']],
    text=yearly_df['sharpe'].round(2), textposition='outside', name='Sharpe'), row=1, col=2)
fig_yr.update_layout(
    title="Annual Performance (Best Config)",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12), height=400, showlegend=False,
)
for ann in fig_yr.layout.annotations:
    ann.font.color = TEXT_CLR

# --- Fig 4: Gap Size Distribution ---
fig_gap = make_subplots(rows=1, cols=2,
    subplot_titles=["Gap Size Distribution", "Win Rate by Gap Size Bucket"])
fig_gap.add_trace(go.Histogram(
    x=daily_info['gap_abs'], nbinsx=40,
    marker_color=ACCENT, opacity=0.8, name='Gap Size'
), row=1, col=1)

# Bucket win rate
best_trades['gap_bucket'] = pd.cut(best_trades['gap_abs'],
    bins=[0, 5, 10, 15, 20, 30, 50, 200], labels=['<5','5-10','10-15','15-20','20-30','30-50','>50'])
bucket_wr = best_trades.groupby('gap_bucket', observed=True).agg(
    wr=('pnl', lambda x: (x > 0).mean()),
    n=('pnl', 'count'),
    avg_pnl=('pnl', 'mean'),
).reset_index()
fig_gap.add_trace(go.Bar(
    x=bucket_wr['gap_bucket'].astype(str),
    y=bucket_wr['wr'] * 100,
    marker_color=[GREEN if w >= 50 else RED_CLR for w in bucket_wr['wr'] * 100],
    text=[f"{w:.1f}%\n(n={n})" for w, n in zip(bucket_wr['wr'] * 100, bucket_wr['n'])],
    textposition='outside', name='WR%'
), row=1, col=2)
fig_gap.add_hline(y=50, line_dash="dot", line_color="#888", row=1, col=2)
fig_gap.update_layout(
    title="Gap Statistics",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12), height=400, showlegend=False,
)
for ann in fig_gap.layout.annotations:
    ann.font.color = TEXT_CLR

# --- Fig 5: PnL distribution ---
best_trades_pnl = best_trades['pnl']
fig_pnl_dist = go.Figure()
fig_pnl_dist.add_trace(go.Histogram(
    x=best_trades_pnl[best_trades_pnl > 0], name='Win', marker_color=GREEN, opacity=0.75, nbinsx=30))
fig_pnl_dist.add_trace(go.Histogram(
    x=best_trades_pnl[best_trades_pnl <= 0], name='Loss', marker_color=RED_CLR, opacity=0.75, nbinsx=30))
fig_pnl_dist.add_vline(x=0, line_color='#888', line_dash='dash')
fig_pnl_dist.update_layout(
    barmode='overlay',
    title="PnL Distribution (Win vs Loss)",
    xaxis_title="PnL (points)", yaxis_title="Count",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=13), height=380,
)

# --- Fig 6: Exit reason breakdown ---
exit_counts = best_trades.groupby('exit_reason')['pnl'].agg(['count', 'mean', 'sum']).reset_index()
fig_exit = make_subplots(rows=1, cols=2, subplot_titles=["Exit Reason Count", "Avg PnL by Exit"])
fig_exit.add_trace(go.Bar(
    x=exit_counts['exit_reason'], y=exit_counts['count'],
    marker_color=ACCENT, text=exit_counts['count'], textposition='outside',
), row=1, col=1)
fig_exit.add_trace(go.Bar(
    x=exit_counts['exit_reason'], y=exit_counts['mean'],
    marker_color=[GREEN if v > 0 else RED_CLR for v in exit_counts['mean']],
    text=exit_counts['mean'].round(2), textposition='outside',
), row=1, col=2)
fig_exit.update_layout(
    title="Exit Reason Analysis",
    paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_CLR, size=12), height=380, showlegend=False,
)
for ann in fig_exit.layout.annotations:
    ann.font.color = TEXT_CLR

# =============================================================================
# --- ASSEMBLE HTML ---
# =============================================================================
best_stats  = calc_stats(best_trades['pnl'].reset_index(drop=True), 'Best')
best20_stats = calc_stats(best_trades[best_trades['gap_abs'] >= 20]['pnl'].reset_index(drop=True), 'Gap>=20')

html_parts = [f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>NQ Gap Fill Strategy</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:'Inter',sans-serif; background:{DARK_BG}; color:{TEXT_CLR}; padding:0 0 60px; }}
    .hero {{
      background:linear-gradient(135deg,#1a1d27 0%,#12151f 60%,#0f1117 100%);
      border-bottom:1px solid #1e2130; padding:48px 40px 36px;
    }}
    .hero h1 {{ font-size:28px; font-weight:700; margin-bottom:8px; }}
    .hero p  {{ color:#94a3b8; font-size:15px; max-width:720px; }}
    .badge {{ display:inline-block; padding:3px 10px; border-radius:99px;
              font-size:12px; font-weight:600; margin-left:10px; vertical-align:middle; }}
    .badge-blue {{ background:#1e3a5f; color:{BLUE_CLR}; }}
    .container {{ max-width:1400px; margin:0 auto; padding:0 32px; }}
    .card {{
      background:{CARD_BG}; border-radius:12px; padding:28px 32px; margin:20px 0;
      border:1px solid #2a2d3a; box-shadow:0 4px 24px rgba(0,0,0,.4);
    }}
    .card h2 {{ margin:0 0 6px; color:{ACCENT}; font-size:18px; letter-spacing:.5px; }}
    .card p  {{ color:#94a3b8; font-size:14px; margin:4px 0 16px; }}
    .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; margin:16px 0; }}
    .kpi {{ background:#12151f; border-radius:10px; padding:18px 20px; border:1px solid #1e2130; }}
    .kpi .val {{ font-size:24px; font-weight:700; }}
    .kpi .lbl {{ font-size:11px; color:#6b7280; margin-top:4px; }}
    .green .val {{ color:{GREEN}; }} .red .val {{ color:{RED_CLR}; }}
    .gold .val  {{ color:{GOLD}; }} .blue .val {{ color:{ACCENT}; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:12px; }}
    th {{ background:#12151f; color:{ACCENT}; padding:10px 14px; text-align:left; border-bottom:2px solid #1e2130; }}
    td {{ padding:9px 14px; border-bottom:1px solid #1e2130; color:{TEXT_CLR}; }}
    tr:hover td {{ background:#12151f; }}
    .pos {{ color:{GREEN}; font-weight:600; }} .neg {{ color:{RED_CLR}; font-weight:600; }}
  </style>
</head>
<body>
<div class="hero"><div class="container">
  <h1>NQ Opening Auction Gap Fill
    <span class="badge badge-blue">2010 - 2025</span>
  </h1>
  <p>當 NQ 開盤相對前日 RTH 收盤出現缺口，做反向回補交易。
     測試不同回補目標（25%-100%）× 停損延伸（5-20pts）組合，
     找出最佳參數並分析各缺口大小的 edge。</p>
</div></div>
<div class="container">
<div class="card">
  <h2>Best Config: Fill={best_fill:.0%} / SL+{best_sl}pts</h2>
  <p>All Gaps vs Gap size filter</p>
  <div class="kpi-grid">
    <div class="kpi {'green' if best_stats['total'] > 0 else 'red'}">
      <div class="val">{best_stats['total']:.0f}</div><div class="lbl">All: Total PnL (pts)</div></div>
    <div class="kpi {'green' if best_stats['wr'] >= 0.5 else 'red'}">
      <div class="val">{best_stats['wr']:.1%}</div><div class="lbl">All: Win Rate</div></div>
    <div class="kpi gold"><div class="val">{best_stats['sharpe']:.3f}</div>
      <div class="lbl">All: Sharpe</div></div>
    <div class="kpi blue"><div class="val">{int(best_stats['n'])}</div>
      <div class="lbl">All: Trades</div></div>
    <div class="kpi {'green' if best20_stats['total'] > 0 else 'red'}">
      <div class="val">{best20_stats['total']:.0f}</div><div class="lbl">Gap>=20: Total PnL</div></div>
    <div class="kpi {'green' if best20_stats['wr'] >= 0.5 else 'red'}">
      <div class="val">{best20_stats['wr']:.1%}</div><div class="lbl">Gap>=20: Win Rate</div></div>
    <div class="kpi gold"><div class="val">{best20_stats['sharpe']:.3f}</div>
      <div class="lbl">Gap>=20: Sharpe</div></div>
    <div class="kpi blue"><div class="val">{int(best20_stats['n'])}</div>
      <div class="lbl">Gap>=20: Trades</div></div>
  </div>
</div>
"""]

for fig_obj in [fig_heat, fig_eq, fig_gap, fig_yr, fig_pnl_dist, fig_exit]:
    html_parts.append(f"<div style='margin:20px 0'>{fig_obj.to_html(full_html=False, include_plotlyjs='cdn')}</div>")

# Full grid table
html_parts.append(f"""<div class="card"><h2>Full Parameter Grid</h2>
<table><thead><tr>
  <th>Fill Target</th><th>SL Extension</th><th>Trades</th>
  <th>Win Rate</th><th>Total PnL</th><th>Sharpe</th><th>Max DD</th><th>PF</th>
</tr></thead><tbody>""")
for _, r in grid_df.sort_values('sharpe', ascending=False).iterrows():
    pnl_cls = 'pos' if r['total'] > 0 else 'neg'
    html_parts.append(f"""<tr>
      <td>{r['fill_target']:.0%}</td><td>+{r['sl_ext']}pts</td>
      <td>{int(r['n'])}</td><td>{r['wr']:.2%}</td>
      <td class="{pnl_cls}">{r['total']:.1f}</td>
      <td>{r['sharpe']:.3f}</td><td class="neg">{r['maxdd']:.1f}</td>
      <td>{r['pf']:.3f}</td></tr>""")
html_parts.append("</tbody></table></div>")
html_parts.append("</div></body></html>")

out_html = os.path.join(OUTPUT_DIR, 'gap_fill_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write('\n'.join(html_parts))

print(f"\n{'='*60}")
print("DONE. Outputs:")
print(f"  Dashboard  : {out_html}")
print(f"  Grid CSV   : {os.path.join(OUTPUT_DIR, 'gap_fill_grid.csv')}")
print(f"  Trades CSV : {os.path.join(OUTPUT_DIR, 'gap_fill_best_trades.csv')}")
print(f"  Yearly CSV : {os.path.join(OUTPUT_DIR, 'gap_fill_yearly.csv')}")
print("=" * 60)
