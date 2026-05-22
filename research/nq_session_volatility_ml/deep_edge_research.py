"""
Deep Dive Quantitative Edge Research
Analyzing NQ Futures for actionable structural edges.
"""
import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet"
OUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\nq_session_volatility_ml"

print("Loading data for deep edge research...")
df = pd.read_parquet(DATA_PATH, columns=['ts_event', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
df = df[~df['symbol'].str.contains('-')].copy()
df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')
df = df[df['ts_event'] >= '2019-10-01'].copy()
df['trading_date_dt'] = df['ts_event'] + pd.Timedelta(hours=6)
df['tdate'] = df['trading_date_dt'].dt.date
df['nyt'] = df['ts_event'].dt.hour * 100 + df['ts_event'].dt.minute

print("Processing session aggregations and times...")
# Split sessions
asia = df[(df['nyt'] >= 1800) | (df['nyt'] < 300)]
euro = df[(df['nyt'] >= 300) & (df['nyt'] < 930)]
us   = df[(df['nyt'] >= 930) & (df['nyt'] <= 1600)]
us_first_30 = us[us['nyt'] < 1000]

def get_session_stats(sdf):
    agg = sdf.groupby('tdate').agg(
        o=('open', 'first'),
        h=('high', 'max'),
        l=('low', 'min'),
        c=('close', 'last'),
        v=('volume', 'sum')
    )
    return agg

asia_stats = get_session_stats(asia).add_prefix('asia_')
euro_stats = get_session_stats(euro).add_prefix('euro_')
us_stats = get_session_stats(us).add_prefix('us_')
us_30_stats = get_session_stats(us_first_30).add_prefix('us30_')

# Advanced US metrics (High/Low Time)
def get_extreme_times(group):
    h_idx = group['high'].idxmax()
    l_idx = group['low'].idxmin()
    return pd.Series({
        'us_h_time': group.loc[h_idx, 'nyt'] if pd.notnull(h_idx) else np.nan,
        'us_l_time': group.loc[l_idx, 'nyt'] if pd.notnull(l_idx) else np.nan
    })

us_times = us.groupby('tdate').apply(get_extreme_times)

# Merge everything
daily = pd.concat([asia_stats, euro_stats, us_stats, us_30_stats, us_times], axis=1).dropna()
daily['prev_us_c'] = daily['us_c'].shift(1)
daily['prev_us_h'] = daily['us_h'].shift(1)
daily['prev_us_l'] = daily['us_l'].shift(1)
daily = daily.dropna()

print(f"Total valid trading days: {len(daily)}")

dashboard_data = {}

# ==============================================================================
# Edge 1: Directional Bias (Trend Continuation vs Reversion)
# ==============================================================================
print("Analyzing Edge 1: Directional Bias...")
daily['euro_trend'] = (daily['euro_c'] - daily['euro_o']) / daily['euro_o'] * 100
daily['us30_trend'] = (daily['us30_c'] - daily['us30_o']) / daily['us30_o'] * 100
daily['us_trend'] = (daily['us_c'] - daily['us_o']) / daily['us_o'] * 100

def get_concordance(cond_mask, trend_col):
    subset = daily[cond_mask]
    if len(subset) == 0: return {"n": 0, "cont": 0, "rev": 0}
    # Continuation: same sign. Reversal: opposite sign
    same_sign = (np.sign(subset['euro_trend']) == np.sign(subset[trend_col])).mean()
    return {"n": len(subset), "cont": same_sign, "rev": 1 - same_sign}

e1_bins = [
    ("Strong Bull Euro (>0.8%)", daily['euro_trend'] > 0.8),
    ("Moderate Bull Euro (0.3% - 0.8%)", (daily['euro_trend'] > 0.3) & (daily['euro_trend'] <= 0.8)),
    ("Flat (-0.3% - 0.3%)", (daily['euro_trend'] >= -0.3) & (daily['euro_trend'] <= 0.3)),
    ("Moderate Bear Euro (-0.8% - -0.3%)", (daily['euro_trend'] >= -0.8) & (daily['euro_trend'] < -0.3)),
    ("Strong Bear Euro (<-0.8%)", daily['euro_trend'] < -0.8)
]

e1_results = []
for label, mask in e1_bins:
    us30 = get_concordance(mask, 'us30_trend')
    usFull = get_concordance(mask, 'us_trend')
    e1_results.append({
        "label": label,
        "n": us30["n"],
        "us30_cont": us30["cont"],
        "us_full_cont": usFull["cont"]
    })
dashboard_data['edge1_directional'] = e1_results

# ==============================================================================
# Edge 2: Gap Dynamics (Gap Fade vs Gap & Go)
# ==============================================================================
print("Analyzing Edge 2: Gap Dynamics...")
daily['gap_pct'] = (daily['us_o'] - daily['prev_us_c']) / daily['prev_us_c'] * 100
daily['gap_size'] = daily['gap_pct'].abs()

# Fade success: Gap Up -> low goes below prev_close. Gap Down -> high goes above prev_close
daily['gap_faded'] = np.where(
    daily['gap_pct'] > 0, 
    daily['us_l'] <= daily['prev_us_c'],
    np.where(daily['gap_pct'] < 0, daily['us_h'] >= daily['prev_us_c'], False)
)

# Volume percentile (Euro session) to filter
daily['euro_vol_pctile'] = daily['euro_v'].rolling(20, min_periods=5).rank(pct=True)

e2_bins = pd.qcut(daily['gap_size'], q=4, labels=['Small Gap', 'Medium Gap', 'Large Gap', 'Extreme Gap'])
daily['gap_bucket'] = e2_bins

e2_results = []
for bucket in ['Small Gap', 'Medium Gap', 'Large Gap', 'Extreme Gap']:
    subset = daily[daily['gap_bucket'] == bucket]
    if len(subset) == 0: continue
    
    # Baseline fade probability
    fade_prob = subset['gap_faded'].mean()
    
    # Conditional on Euro Volume
    high_vol = subset[subset['euro_vol_pctile'] > 0.8]['gap_faded'].mean()
    low_vol = subset[subset['euro_vol_pctile'] < 0.2]['gap_faded'].mean()
    
    e2_results.append({
        "gap_bucket": bucket,
        "avg_gap_pct": subset['gap_size'].mean(),
        "n": len(subset),
        "fade_prob_overall": fade_prob,
        "fade_prob_high_vol": high_vol,
        "fade_prob_low_vol": low_vol
    })
dashboard_data['edge2_gap'] = e2_results

# ==============================================================================
# Edge 3: Volatility Coiling (Extreme Compression)
# ==============================================================================
print("Analyzing Edge 3: Volatility Coiling...")
daily['asia_range_pct'] = (daily['asia_h'] - daily['asia_l']) / daily['asia_o'] * 100
daily['euro_range_pct'] = (daily['euro_h'] - daily['euro_l']) / daily['euro_o'] * 100
daily['pre_vol'] = daily['asia_range_pct'] + daily['euro_range_pct']

# Z-score of pre-market volatility (60-day rolling to capture regime)
daily['pre_vol_z'] = (daily['pre_vol'] - daily['pre_vol'].rolling(60, min_periods=20).mean()) / daily['pre_vol'].rolling(60, min_periods=20).std()

# Trend Day Definition: CLV > 0.85 (Strong up) or CLV < 0.15 (Strong down)
# CLV (Close Location Value) = (Close - Low) / (High - Low)
daily['us_range'] = daily['us_h'] - daily['us_l']
daily['clv'] = np.where(daily['us_range'] > 0, (daily['us_c'] - daily['us_l']) / daily['us_range'], 0.5)
daily['is_trend_day'] = (daily['clv'] > 0.85) | (daily['clv'] < 0.15)

# Also check average US Range Expansion
daily['us_range_pct'] = daily['us_range'] / daily['us_o'] * 100

def get_coiling_stats(mask):
    subset = daily[mask]
    if len(subset) == 0: return {}
    return {
        "n": len(subset),
        "trend_day_prob": subset['is_trend_day'].mean(),
        "avg_us_range_pct": subset['us_range_pct'].mean()
    }

e3_results = [
    {"label": "Extreme Compression (Z < -1.5)", **get_coiling_stats(daily['pre_vol_z'] < -1.5)},
    {"label": "Compression (Z -1.5 to -0.5)", **get_coiling_stats((daily['pre_vol_z'] >= -1.5) & (daily['pre_vol_z'] < -0.5))},
    {"label": "Normal (Z -0.5 to 0.5)", **get_coiling_stats((daily['pre_vol_z'] >= -0.5) & (daily['pre_vol_z'] <= 0.5))},
    {"label": "Expansion (Z 0.5 to 1.5)", **get_coiling_stats((daily['pre_vol_z'] > 0.5) & (daily['pre_vol_z'] <= 1.5))},
    {"label": "Extreme Expansion (Z > 1.5)", **get_coiling_stats(daily['pre_vol_z'] > 1.5)}
]
dashboard_data['edge3_coiling'] = [r for r in e3_results if 'n' in r]

# ==============================================================================
# Edge 4: Time of Day (When do Highs/Lows form?)
# ==============================================================================
print("Analyzing Edge 4: Time of Day...")
def categorize_time(t):
    if pd.isna(t): return "Unknown"
    if 930 <= t < 1000: return "09:30-10:00 (ORB)"
    if 1000 <= t < 1130: return "10:00-11:30 (Morning)"
    if 1130 <= t < 1400: return "11:30-14:00 (Midday)"
    return "14:00-16:00 (Afternoon)"

daily['h_time_cat'] = daily['us_h_time'].apply(categorize_time)
daily['l_time_cat'] = daily['us_l_time'].apply(categorize_time)

# We want to know if the pre-market volatility changes this distribution
pre_vol_q = pd.qcut(daily['pre_vol'], q=3, labels=['Low Pre-Vol', 'Normal Pre-Vol', 'High Pre-Vol'])
daily['pre_vol_regime'] = pre_vol_q

e4_results = []
for regime in ['Low Pre-Vol', 'Normal Pre-Vol', 'High Pre-Vol']:
    subset = daily[daily['pre_vol_regime'] == regime]
    if len(subset) == 0: continue
    
    h_dist = subset['h_time_cat'].value_counts(normalize=True).to_dict()
    l_dist = subset['l_time_cat'].value_counts(normalize=True).to_dict()
    
    e4_results.append({
        "regime": regime,
        "n": len(subset),
        "high_dist": h_dist,
        "low_dist": l_dist
    })

dashboard_data['edge4_tod'] = e4_results

# Export Data
import os
out_file = os.path.join(OUT_DIR, 'edge_dashboard_data.json')
with open(out_file, 'w') as f:
    json.dump(dashboard_data, f, default=str)

print(f"Edge research completed! Data saved to {out_file}")
