"""
NQ Session Volatility ML Analysis
Asian/European session → US session volatility prediction
"""
import numpy as np, pandas as pd, json, warnings
warnings.filterwarnings('ignore')
from xgboost import XGBRegressor, XGBClassifier
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, mean_absolute_error, accuracy_score, f1_score
from scipy import stats as sp_stats

DATA = r"C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet"
OUT  = r"C:\Users\user\.gemini\antigravity\scratch\nq_session_volatility_ml"

print("Loading data...")
df = pd.read_parquet(DATA, columns=['ts_event','symbol','open','high','low','close','volume','vwap'])
df = df[~df['symbol'].str.contains('-')].copy()
df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')
df = df[df['ts_event'] >= '2019-10-01'].copy()
df['trading_date_dt'] = df['ts_event'] + pd.Timedelta(hours=6)
df['tdate'] = df['trading_date_dt'].dt.date
df['nyt'] = df['ts_event'].dt.hour * 100 + df['ts_event'].dt.minute
print(f"  Loaded {len(df):,} rows")

# Session splits
asia = df[(df['nyt'] >= 1800) | (df['nyt'] < 300)]
euro = df[(df['nyt'] >= 300) & (df['nyt'] < 930)]
us   = df[(df['nyt'] >= 930) & (df['nyt'] <= 1600)]

def sess_stats(sdf, prefix):
    g = sdf.groupby('tdate').agg(
        o=('open','first'), h=('high','max'), l=('low','min'),
        c=('close','last'), v=('volume','sum')
    ).dropna()
    g[f'{prefix}_range'] = g['h'] - g['l']
    g[f'{prefix}_range_pct'] = g[f'{prefix}_range'] / g['o'] * 100
    g[f'{prefix}_trend'] = g['c'] - g['o']
    g[f'{prefix}_trend_pct'] = (g['c'] - g['o']) / g['o'] * 100
    r = g[f'{prefix}_range']
    g[f'{prefix}_body_ratio'] = (g['c'] - g['o']).abs() / g[f'{prefix}_range'].replace(0, np.nan)
    g[f'{prefix}_volume'] = g['v']
    g[f'{prefix}_range_z'] = (r - r.rolling(20,min_periods=5).mean()) / r.rolling(20,min_periods=5).std()
    cols = [c for c in g.columns if c.startswith(prefix)]
    return g[cols]

print("Computing session features...")
asia_f = sess_stats(asia, 'asia')
euro_f = sess_stats(euro, 'euro')
us_f   = sess_stats(us, 'us')

feat = asia_f.join(euro_f, how='inner').join(us_f, how='inner').dropna()
feat['asia_euro_ratio'] = feat['asia_range'] / feat['euro_range'].replace(0, np.nan)
feat['combined_range'] = feat['asia_range'] + feat['euro_range']
feat['combined_range_pct'] = feat['asia_range_pct'] + feat['euro_range_pct']
feat['prev_us_range'] = feat['us_range'].shift(1)
feat['prev_us_range_pct'] = feat['us_range_pct'].shift(1)
feat['dow'] = pd.to_datetime(feat.index).dayofweek
feat = feat.dropna()

# Targets
feat['us_high_vol'] = (feat['us_range_pct'] > feat['us_range_pct'].rolling(20,min_periods=5).mean()).astype(int)
q33 = feat['us_range_pct'].quantile(0.33)
q66 = feat['us_range_pct'].quantile(0.66)
feat['us_regime'] = pd.cut(feat['us_range_pct'], bins=[-np.inf, q33, q66, np.inf], labels=[0,1,2]).astype(int)
print(f"  Dataset: {len(feat)} days")

# Features
x_cols = [c for c in feat.columns if c.startswith(('asia_','euro_','combined','prev_us','dow')) and 'us_' not in c.replace('prev_us','prevus')]
x_cols = [c for c in x_cols if c not in ['us_range','us_range_pct','us_trend','us_trend_pct','us_body_ratio','us_volume','us_range_z','us_high_vol','us_regime']]
# fix prev_us columns
x_cols = [c for c in feat.columns if any(c.startswith(p) for p in ['asia_','euro_','combined_','prev_us_','dow']) ]
print(f"  Features ({len(x_cols)}): {x_cols}")

# --- Correlation Analysis ---
print("Correlation analysis...")
targets = ['us_range','us_range_pct']
corr_data = feat[x_cols + targets].corr()
corr_with_target = corr_data.loc[x_cols, targets].sort_values('us_range_pct', ascending=False)

# --- Conditional Distribution ---
asia_q = pd.qcut(feat['asia_range_pct'], q=4, labels=['Q1_Low','Q2','Q3','Q4_High'])
euro_q = pd.qcut(feat['euro_range_pct'], q=4, labels=['Q1_Low','Q2','Q3','Q4_High'])
cond_asia = feat.groupby(asia_q)['us_range_pct'].agg(['mean','median','std','count'])
cond_euro = feat.groupby(euro_q)['us_range_pct'].agg(['mean','median','std','count'])

# --- Granger-like test (simple lagged correlation) ---
from scipy.stats import pearsonr, spearmanr
granger = {}
for col in ['asia_range_pct','euro_range_pct','combined_range_pct']:
    pr, pp = pearsonr(feat[col], feat['us_range_pct'])
    sr, sp = spearmanr(feat[col], feat['us_range_pct'])
    granger[col] = {'pearson_r': pr, 'pearson_p': pp, 'spearman_r': sr, 'spearman_p': sp}

# --- Walk-Forward ML ---
print("Walk-Forward ML training...")
feat['year'] = pd.to_datetime(feat.index).year
years = sorted(feat['year'].unique())
TRAIN_YRS = 3

results = []
feat['xgb_pred'] = np.nan
feat['rf_pred'] = np.nan
feat['ridge_pred'] = np.nan
feat['xgb_cls_pred'] = np.nan
feat['xgb_cls_prob'] = np.nan

fi_all = []

for test_yr in range(years[0]+TRAIN_YRS, years[-1]+1):
    tr = feat[(feat['year'] >= test_yr-TRAIN_YRS) & (feat['year'] < test_yr)]
    te = feat[feat['year'] == test_yr]
    if len(tr) < 50 or len(te) < 10: continue
    
    Xtr, ytr = tr[x_cols].values, tr['us_range_pct'].values
    Xte, yte = te[x_cols].values, te['us_range_pct'].values
    ytr_cls = tr['us_high_vol'].values
    yte_cls = te['us_high_vol'].values
    
    # XGBoost Regressor
    xgb_r = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, verbosity=0, random_state=42)
    xgb_r.fit(Xtr, ytr)
    p_xgb = xgb_r.predict(Xte)
    feat.loc[feat['year']==test_yr, 'xgb_pred'] = p_xgb
    
    # RF Regressor
    rf_r = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42, n_jobs=-1)
    rf_r.fit(Xtr, ytr)
    p_rf = rf_r.predict(Xte)
    feat.loc[feat['year']==test_yr, 'rf_pred'] = p_rf
    
    # Ridge
    ridge = Ridge(alpha=1.0)
    ridge.fit(Xtr, ytr)
    p_ridge = ridge.predict(Xte)
    feat.loc[feat['year']==test_yr, 'ridge_pred'] = p_ridge
    
    # XGBoost Classifier
    xgb_c = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, verbosity=0, random_state=42, eval_metric='logloss')
    xgb_c.fit(Xtr, ytr_cls)
    p_cls = xgb_c.predict(Xte)
    p_prob = xgb_c.predict_proba(Xte)[:,1]
    feat.loc[feat['year']==test_yr, 'xgb_cls_pred'] = p_cls
    feat.loc[feat['year']==test_yr, 'xgb_cls_prob'] = p_prob
    
    r2_xgb = r2_score(yte, p_xgb)
    r2_rf = r2_score(yte, p_rf)
    r2_ridge = r2_score(yte, p_ridge)
    mae_xgb = mean_absolute_error(yte, p_xgb)
    acc = accuracy_score(yte_cls, p_cls)
    
    results.append({'year': test_yr, 'n': len(te), 'r2_xgb': r2_xgb, 'r2_rf': r2_rf, 'r2_ridge': r2_ridge, 'mae_xgb': mae_xgb, 'acc_cls': acc})
    
    fi = pd.Series(xgb_r.feature_importances_, index=x_cols)
    fi_all.append(fi)
    
    print(f"  {test_yr}: n={len(te)}, R2_XGB={r2_xgb:.3f}, R2_RF={r2_rf:.3f}, R2_Ridge={r2_ridge:.3f}, Acc={acc:.1%}")

fi_avg = pd.concat(fi_all, axis=1).mean(axis=1).sort_values(ascending=False)
res_df = pd.DataFrame(results)

# OOS metrics
oos = feat.dropna(subset=['xgb_pred'])
overall_r2_xgb = r2_score(oos['us_range_pct'], oos['xgb_pred'])
overall_r2_rf = r2_score(oos['us_range_pct'], oos['rf_pred'])
overall_r2_ridge = r2_score(oos['us_range_pct'], oos['ridge_pred'])
overall_mae = mean_absolute_error(oos['us_range_pct'], oos['xgb_pred'])
oos_cls = oos.dropna(subset=['xgb_cls_pred'])
overall_acc = accuracy_score(oos_cls['us_high_vol'], oos_cls['xgb_cls_pred'])

print(f"\n=== Overall OOS Results ===")
print(f"  XGBoost R2: {overall_r2_xgb:.4f}")
print(f"  RF R2:      {overall_r2_rf:.4f}")
print(f"  Ridge R2:   {overall_r2_ridge:.4f}")
print(f"  XGB MAE:    {overall_mae:.4f}%")
print(f"  Classifier Acc: {overall_acc:.1%}")

# --- SHAP (simplified: use feature importance as proxy) ---
# --- Quantile analysis ---
asia_qtiles = pd.qcut(feat['asia_range_pct'], q=5, labels=['Very Low','Low','Medium','High','Very High'])
us_by_asia_q = feat.groupby(asia_qtiles)['us_range_pct'].agg(['mean','median','std','count'])
euro_qtiles = pd.qcut(feat['euro_range_pct'], q=5, labels=['Very Low','Low','Medium','High','Very High'])
us_by_euro_q = feat.groupby(euro_qtiles)['us_range_pct'].agg(['mean','median','std','count'])

# --- Monthly heatmap data ---
feat['month'] = pd.to_datetime(feat.index).month
feat['yr'] = pd.to_datetime(feat.index).year
monthly_vol = feat.groupby(['yr','month'])['us_range_pct'].mean().unstack()

# === SAVE ALL DATA FOR DASHBOARD ===
print("\nBuilding dashboard...")

dashboard_data = {
    'kpi': {
        'total_days': int(len(feat)),
        'oos_days': int(len(oos)),
        'r2_xgb': round(overall_r2_xgb, 4),
        'r2_rf': round(overall_r2_rf, 4),
        'r2_ridge': round(overall_r2_ridge, 4),
        'mae_xgb': round(overall_mae, 4),
        'acc_cls': round(overall_acc, 4),
        'pearson_asia': round(granger['asia_range_pct']['pearson_r'], 4),
        'pearson_euro': round(granger['euro_range_pct']['pearson_r'], 4),
        'spearman_asia': round(granger['asia_range_pct']['spearman_r'], 4),
        'spearman_euro': round(granger['euro_range_pct']['spearman_r'], 4),
    },
    'corr_matrix': corr_with_target.reset_index().rename(columns={'index':'feature'}).to_dict('records'),
    'fi': fi_avg.reset_index().rename(columns={'index':'feature', 0:'importance'}).to_dict('records'),
    'wf_results': res_df.to_dict('records'),
    'scatter_xgb': {'actual': oos['us_range_pct'].tolist(), 'pred': oos['xgb_pred'].tolist(), 'dates': [str(d) for d in oos.index]},
    'scatter_rf': {'actual': oos['us_range_pct'].tolist(), 'pred': oos['rf_pred'].tolist()},
    'timeseries': {'dates': [str(d) for d in oos.index], 'actual': oos['us_range_pct'].tolist(), 'xgb': oos['xgb_pred'].tolist(), 'rf': oos['rf_pred'].tolist()},
    'cond_asia': {str(k): {'mean': round(v['mean'],4), 'median': round(v['median'],4), 'std': round(v['std'],4), 'count': int(v['count'])} for k, v in cond_asia.iterrows()},
    'cond_euro': {str(k): {'mean': round(v['mean'],4), 'median': round(v['median'],4), 'std': round(v['std'],4), 'count': int(v['count'])} for k, v in cond_euro.iterrows()},
    'quantile_asia': us_by_asia_q.reset_index().rename(columns={'asia_range_pct':'quantile'}).to_dict('records'),
    'quantile_euro': us_by_euro_q.reset_index().rename(columns={'euro_range_pct':'quantile'}).to_dict('records'),
    'monthly_heatmap': {'years': monthly_vol.index.tolist(), 'months': monthly_vol.columns.tolist(), 'values': monthly_vol.fillna(0).values.tolist()},
    'cls_prob': {'prob': oos_cls['xgb_cls_prob'].tolist(), 'actual': oos_cls['us_high_vol'].astype(int).tolist()},
    'full_corr': corr_data.loc[x_cols, x_cols].reset_index().to_dict('records'),
    'granger': granger,
    'dow_analysis': feat.groupby('dow')['us_range_pct'].agg(['mean','median','std']).reset_index().to_dict('records'),
}

import os
with open(os.path.join(OUT, 'dashboard_data.json'), 'w') as f:
    json.dump(dashboard_data, f, default=str)

print("Data saved. Generating HTML...")
