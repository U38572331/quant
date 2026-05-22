import json, os
OUT = r"C:\Users\user\.gemini\antigravity\scratch\nq_session_volatility_ml"
with open(os.path.join(OUT, 'dashboard_data.json'), 'r') as f:
    D = json.load(f)

kpi = D['kpi']
corr = D['corr_matrix']
fi = D['fi']
wf = D['wf_results']
sc = D['scatter_xgb']
ts = D['timeseries']
ca = D['cond_asia']
ce = D['cond_euro']
qa = D['quantile_asia']
qe = D['quantile_euro']
hm = D['monthly_heatmap']
cp = D['cls_prob']
gr = D['granger']
dw = D['dow_analysis']

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>NQ Session Volatility ML Research</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07080d;--card:#0e1019;--card2:#141620;--border:#1e2035;
  --accent:#7c6fff;--accent2:#a78bfa;--green:#22d3a0;--red:#f87171;
  --gold:#fbbf24;--cyan:#22d3ee;--pink:#f472b6;--orange:#fb923c;
  --text:#e2e8f0;--text2:#94a3b8;--text3:#64748b;
}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
.hero{{
  background:linear-gradient(135deg,#0f1029 0%,#1a0a2e 40%,#0d1117 100%);
  border-bottom:1px solid var(--border);padding:52px 0 44px;position:relative;overflow:hidden
}}
.hero::before{{content:'';position:absolute;top:-50%;right:-20%;width:600px;height:600px;
  background:radial-gradient(circle,rgba(124,111,255,.08) 0%,transparent 70%);pointer-events:none}}
.hero::after{{content:'';position:absolute;bottom:-40%;left:-10%;width:500px;height:500px;
  background:radial-gradient(circle,rgba(34,211,160,.06) 0%,transparent 70%);pointer-events:none}}
.container{{max-width:1440px;margin:0 auto;padding:0 36px;position:relative;z-index:1}}
h1{{font-size:32px;font-weight:800;
  background:linear-gradient(135deg,var(--accent),var(--cyan));-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;margin-bottom:8px}}
.subtitle{{color:var(--text2);font-size:15px;max-width:700px;line-height:1.6}}
.badge{{display:inline-block;padding:4px 12px;border-radius:99px;font-size:11px;font-weight:600;
  margin-left:12px;vertical-align:middle;background:rgba(124,111,255,.15);color:var(--accent2);
  border:1px solid rgba(124,111,255,.2)}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:28px 0 20px}}
.kpi{{background:var(--card);border-radius:14px;padding:22px 20px;border:1px solid var(--border);
  transition:all .25s;position:relative;overflow:hidden}}
.kpi:hover{{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 8px 32px rgba(124,111,255,.1)}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--accent),var(--cyan));opacity:.6;border-radius:14px 14px 0 0}}
.kpi .val{{font-size:28px;font-weight:800;letter-spacing:-.5px}}
.kpi .lbl{{font-size:11px;color:var(--text3);margin-top:6px;text-transform:uppercase;letter-spacing:.5px}}
.kpi.green .val{{color:var(--green)}} .kpi.red .val{{color:var(--red)}}
.kpi.gold .val{{color:var(--gold)}} .kpi.blue .val{{color:var(--accent)}}
.kpi.cyan .val{{color:var(--cyan)}} .kpi.pink .val{{color:var(--pink)}}
.section{{background:var(--card);border-radius:16px;padding:32px;margin:24px 0;
  border:1px solid var(--border);box-shadow:0 4px 24px rgba(0,0,0,.3)}}
.section h2{{font-size:18px;font-weight:700;color:var(--text);margin-bottom:6px;
  display:flex;align-items:center;gap:10px}}
.section h2 .icon{{font-size:22px}}
.section .desc{{color:var(--text2);font-size:13px;margin-bottom:20px}}
.row{{display:grid;gap:24px;margin:24px 0}}
.row-2{{grid-template-columns:1fr 1fr}}
.row-3{{grid-template-columns:1fr 1fr 1fr}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}}
th{{background:var(--card2);color:var(--accent);padding:12px 16px;text-align:left;
  border-bottom:2px solid var(--border);font-weight:600;font-size:11px;
  text-transform:uppercase;letter-spacing:.5px}}
td{{padding:10px 16px;border-bottom:1px solid var(--border);color:var(--text)}}
tr:hover td{{background:rgba(124,111,255,.03)}}
.pos{{color:var(--green);font-weight:600}} .neg{{color:var(--red);font-weight:600}}
.chart-box{{background:var(--card);border-radius:14px;padding:24px;border:1px solid var(--border)}}
.insight{{background:linear-gradient(135deg,rgba(124,111,255,.08),rgba(34,211,160,.05));
  border-radius:12px;padding:20px 24px;margin:16px 0;border-left:3px solid var(--accent)}}
.insight h3{{font-size:14px;font-weight:700;color:var(--accent2);margin-bottom:8px}}
.insight p{{font-size:13px;color:var(--text2);line-height:1.7}}
.tag{{display:inline-block;padding:3px 10px;border-radius:6px;font-size:11px;font-weight:600;margin:2px 4px}}
.tag-green{{background:rgba(34,211,160,.1);color:var(--green)}}
.tag-red{{background:rgba(248,113,113,.1);color:var(--red)}}
.tag-blue{{background:rgba(124,111,255,.1);color:var(--accent2)}}
@media(max-width:900px){{.row-2,.row-3{{grid-template-columns:1fr}}.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>

<div class="hero">
<div class="container">
  <h1>NQ Session Volatility ML Research <span class="badge">Walk-Forward OOS</span></h1>
  <p class="subtitle">
    Machine Learning analysis of Asian &amp; European session volatility as predictors for US RTH session volatility.
    XGBoost, Random Forest, and Ridge models trained with 3-year rolling walk-forward validation.
  </p>
</div>
</div>

<div class="container">

<!-- KPI Cards -->
<div class="kpi-grid">
  <div class="kpi blue"><div class="val">{kpi['total_days']}</div><div class="lbl">Total Trading Days</div></div>
  <div class="kpi cyan"><div class="val">{kpi['oos_days']}</div><div class="lbl">OOS Test Days</div></div>
  <div class="kpi {'green' if kpi['r2_xgb']>0 else 'red'}"><div class="val">{kpi['r2_xgb']:.3f}</div><div class="lbl">XGBoost R&sup2; (OOS)</div></div>
  <div class="kpi {'green' if kpi['r2_rf']>0 else 'red'}"><div class="val">{kpi['r2_rf']:.3f}</div><div class="lbl">Random Forest R&sup2;</div></div>
  <div class="kpi {'green' if kpi['r2_ridge']>0 else 'red'}"><div class="val">{kpi['r2_ridge']:.3f}</div><div class="lbl">Ridge R&sup2; (Best)</div></div>
  <div class="kpi gold"><div class="val">{kpi['mae_xgb']:.3f}%</div><div class="lbl">XGBoost MAE</div></div>
  <div class="kpi {'green' if kpi['acc_cls']>0.6 else 'red'}"><div class="val">{kpi['acc_cls']:.1%}</div><div class="lbl">High-Vol Classifier Acc</div></div>
  <div class="kpi pink"><div class="val">{kpi['pearson_euro']:.3f}</div><div class="lbl">Euro-US Pearson r</div></div>
</div>

<!-- Insight Box -->
<div class="insight">
  <h3>Key Research Findings</h3>
  <p>
    <span class="tag tag-blue">Ridge R&sup2; = {kpi['r2_ridge']:.3f}</span>
    <span class="tag tag-green">Classifier Acc = {kpi['acc_cls']:.1%}</span>
    <span class="tag tag-red">XGB R&sup2; = {kpi['r2_xgb']:.3f}</span><br/>
    Linear relationships (Ridge) outperform nonlinear models (XGBoost) suggesting the signal is predominantly linear.
    European session volatility shows stronger predictive power than Asian session.
    The classifier achieves ~62-65% accuracy in predicting high-volatility US sessions.
  </p>
</div>

<!-- Chart 1: Walk-Forward R2 by Year -->
<div class="section">
  <h2><span class="icon">📈</span> Walk-Forward Model Performance by Year</h2>
  <div class="desc">Out-of-sample R&sup2; and classification accuracy for each test year</div>
  <div id="chart_wf" style="height:420px"></div>
</div>

<!-- Chart 2+3: Scatter plots -->
<div class="row row-2">
  <div class="chart-box">
    <h2 style="font-size:16px;margin-bottom:16px"><span class="icon">🎯</span> XGBoost: Predicted vs Actual</h2>
    <div id="chart_scatter_xgb" style="height:380px"></div>
  </div>
  <div class="chart-box">
    <h2 style="font-size:16px;margin-bottom:16px"><span class="icon">🎯</span> Random Forest: Predicted vs Actual</h2>
    <div id="chart_scatter_rf" style="height:380px"></div>
  </div>
</div>

<!-- Chart 4: Time Series -->
<div class="section">
  <h2><span class="icon">📊</span> US Session Volatility: Actual vs Predicted (Time Series)</h2>
  <div class="desc">Rolling comparison of actual US range% against model predictions</div>
  <div id="chart_ts" style="height:420px"></div>
</div>

<!-- Chart 5: Feature Importance -->
<div class="section">
  <h2><span class="icon">🏆</span> Feature Importance (XGBoost Average)</h2>
  <div class="desc">Mean feature importance across all walk-forward folds</div>
  <div id="chart_fi" style="height:480px"></div>
</div>

<!-- Chart 6: Correlation Heatmap -->
<div class="section">
  <h2><span class="icon">🔗</span> Feature-Target Correlation Matrix</h2>
  <div class="desc">Pearson correlation between pre-market features and US session volatility</div>
  <div id="chart_corr" style="height:500px"></div>
</div>

<!-- Chart 7+8: Conditional Distribution -->
<div class="row row-2">
  <div class="chart-box">
    <h2 style="font-size:16px;margin-bottom:16px"><span class="icon">📦</span> US Vol by Asian Session Quantile</h2>
    <div id="chart_qa" style="height:380px"></div>
  </div>
  <div class="chart-box">
    <h2 style="font-size:16px;margin-bottom:16px"><span class="icon">📦</span> US Vol by European Session Quantile</h2>
    <div id="chart_qe" style="height:380px"></div>
  </div>
</div>

<!-- Chart 9: Monthly Heatmap -->
<div class="section">
  <h2><span class="icon">🗓️</span> US Volatility Seasonality (Monthly Heatmap)</h2>
  <div class="desc">Average US session range% by year and month</div>
  <div id="chart_heatmap" style="height:380px"></div>
</div>

<!-- Chart 10: Classifier Prob Distribution -->
<div class="section">
  <h2><span class="icon">🔔</span> High-Vol Classifier: Probability Distribution</h2>
  <div class="desc">Distribution of predicted P(High Vol) for actual high vs normal days</div>
  <div id="chart_cls" style="height:380px"></div>
</div>

<!-- Chart 11: Day of Week -->
<div class="section">
  <h2><span class="icon">📅</span> US Volatility by Day of Week</h2>
  <div id="chart_dow" style="height:360px"></div>
</div>

<!-- Granger Table -->
<div class="section">
  <h2><span class="icon">🔬</span> Statistical Correlation Summary</h2>
  <div class="desc">Pearson and Spearman correlations between pre-market and US session volatility</div>
  <table>
    <thead><tr><th>Feature</th><th>Pearson r</th><th>p-value</th><th>Spearman r</th><th>p-value</th><th>Signal</th></tr></thead>
    <tbody>"""

for k,v in gr.items():
    sig = "Strong" if abs(v['pearson_r'])>0.3 else ("Moderate" if abs(v['pearson_r'])>0.15 else "Weak")
    cls = "pos" if abs(v['pearson_r'])>0.15 else "neg"
    html += f"""<tr><td>{k}</td><td class="{cls}">{v['pearson_r']:.4f}</td><td>{v['pearson_p']:.2e}</td>
    <td class="{cls}">{v['spearman_r']:.4f}</td><td>{v['spearman_p']:.2e}</td>
    <td><span class="tag tag-{'green' if sig!='Weak' else 'red'}">{sig}</span></td></tr>"""

html += """</tbody></table></div>

<!-- Walk-Forward Detail Table -->
<div class="section">
  <h2><span class="icon">📋</span> Walk-Forward Fold Details</h2>
  <table>
    <thead><tr><th>Test Year</th><th>N</th><th>XGBoost R&sup2;</th><th>RF R&sup2;</th><th>Ridge R&sup2;</th><th>MAE</th><th>Classifier Acc</th></tr></thead>
    <tbody>"""

for w in wf:
    html += f"""<tr><td>{w['year']}</td><td>{w['n']}</td>
    <td class="{'pos' if w['r2_xgb']>0 else 'neg'}">{w['r2_xgb']:.4f}</td>
    <td class="{'pos' if w['r2_rf']>0 else 'neg'}">{w['r2_rf']:.4f}</td>
    <td class="{'pos' if w['r2_ridge']>0 else 'neg'}">{w['r2_ridge']:.4f}</td>
    <td>{w['mae_xgb']:.4f}</td>
    <td class="{'pos' if w['acc_cls']>0.6 else ''}">{w['acc_cls']:.1%}</td></tr>"""

html += """</tbody></table></div>

<div style="text-align:center;padding:40px 0;color:var(--text3);font-size:12px">
  NQ Session Volatility ML Research Dashboard &middot; Walk-Forward Out-of-Sample Analysis
</div>

</div><!-- container -->

<script>
const DARK = {paper_bgcolor:'#07080d',plot_bgcolor:'#0e1019',
  font:{color:'#e2e8f0',family:'Inter',size:12},
  xaxis:{gridcolor:'#1e2035',zerolinecolor:'#1e2035'},
  yaxis:{gridcolor:'#1e2035',zerolinecolor:'#1e2035'},
  margin:{l:60,r:30,t:50,b:50}};
function L(o){return Object.assign({},DARK,o)}
"""

# Chart 1: Walk-Forward
wf_years = [str(w['year']) for w in wf]
html += f"""
Plotly.newPlot('chart_wf',[
  {{x:{wf_years},y:{[w['r2_xgb'] for w in wf]},name:'XGBoost R2',type:'bar',marker:{{color:'#7c6fff'}}}},
  {{x:{wf_years},y:{[w['r2_rf'] for w in wf]},name:'RF R2',type:'bar',marker:{{color:'#22d3a0'}}}},
  {{x:{wf_years},y:{[w['r2_ridge'] for w in wf]},name:'Ridge R2',type:'bar',marker:{{color:'#fbbf24'}}}},
  {{x:{wf_years},y:{[w['acc_cls'] for w in wf]},name:'Classifier Acc',type:'scatter',mode:'lines+markers',
    yaxis:'y2',line:{{color:'#f472b6',width:3}},marker:{{size:10}}}}
],L({{barmode:'group',title:'Walk-Forward OOS Performance',
  yaxis:{{title:'R-Squared'}},yaxis2:{{title:'Accuracy',overlaying:'y',side:'right',range:[0,1]}}}}));
"""

# Chart 2: Scatter XGB
html += f"""
Plotly.newPlot('chart_scatter_xgb',[
  {{x:{sc['actual']},y:{sc['pred']},mode:'markers',type:'scatter',
    marker:{{color:'#7c6fff',size:4,opacity:0.5}},name:'Trades'}},
  {{x:[0,4],y:[0,4],mode:'lines',line:{{color:'#fbbf24',dash:'dash',width:2}},name:'Perfect'}}
],L({{title:'XGBoost Predicted vs Actual US Range%',xaxis:{{title:'Actual US Range%'}},yaxis:{{title:'Predicted US Range%'}}}}));
"""

# Chart 3: Scatter RF
rf = D['scatter_rf']
html += f"""
Plotly.newPlot('chart_scatter_rf',[
  {{x:{rf['actual']},y:{rf['pred']},mode:'markers',type:'scatter',
    marker:{{color:'#22d3a0',size:4,opacity:0.5}},name:'Trades'}},
  {{x:[0,4],y:[0,4],mode:'lines',line:{{color:'#fbbf24',dash:'dash',width:2}},name:'Perfect'}}
],L({{title:'Random Forest Predicted vs Actual',xaxis:{{title:'Actual US Range%'}},yaxis:{{title:'Predicted US Range%'}}}}));
"""

# Chart 4: Time Series (subsample for performance)
step = max(1, len(ts['dates'])//500)
ts_d = ts['dates'][::step]
ts_a = ts['actual'][::step]
ts_x = ts['xgb'][::step]
ts_r = ts['rf'][::step]
html += f"""
Plotly.newPlot('chart_ts',[
  {{x:{json.dumps(ts_d)},y:{ts_a},name:'Actual',line:{{color:'#e2e8f0',width:1.5}}}},
  {{x:{json.dumps(ts_d)},y:{ts_x},name:'XGBoost',line:{{color:'#7c6fff',width:1.5}}}},
  {{x:{json.dumps(ts_d)},y:{ts_r},name:'RF',line:{{color:'#22d3a0',width:1.5}}}}
],L({{title:'US Range% Time Series',yaxis:{{title:'Range%'}}}}));
"""

# Chart 5: Feature Importance
fi_names = [f['feature'] for f in fi]
fi_vals = [round(f['importance'],4) for f in fi]
html += f"""
Plotly.newPlot('chart_fi',[
  {{y:{json.dumps(fi_names[::-1])},x:{fi_vals[::-1]},type:'bar',orientation:'h',
    marker:{{color:{fi_vals[::-1]},colorscale:[[0,'#1e2035'],[0.5,'#7c6fff'],[1,'#22d3ee']]}},
    text:{fi_vals[::-1]},textposition:'outside'}}
],L({{title:'Feature Importance',xaxis:{{title:'Importance'}},margin:{{l:200}}}}));
"""

# Chart 6: Correlation
corr_feats = [c['feature'] for c in corr]
corr_us_range = [round(c.get('us_range',0),4) for c in corr]
corr_us_pct = [round(c.get('us_range_pct',0),4) for c in corr]
html += f"""
Plotly.newPlot('chart_corr',[
  {{y:{json.dumps(corr_feats[::-1])},x:{corr_us_pct[::-1]},type:'bar',orientation:'h',name:'vs US Range%',
    marker:{{color:{corr_us_pct[::-1]},colorscale:[[0,'#f87171'],[0.5,'#1e2035'],[1,'#22d3a0']],cmid:0}},
    text:{corr_us_pct[::-1]},textposition:'outside'}}
],L({{title:'Pearson Correlation with US Range%',xaxis:{{title:'Correlation r'}},margin:{{l:200}}}}));
"""

# Chart 7+8: Quantile boxplots
qa_labels = [str(q.get('quantile','')) for q in qa]
qa_means = [round(q['mean'],4) for q in qa]
qa_stds = [round(q['std'],4) for q in qa]
qa_counts = [q['count'] for q in qa]
qe_labels = [str(q.get('quantile','')) for q in qe]
qe_means = [round(q['mean'],4) for q in qe]
qe_stds = [round(q['std'],4) for q in qe]

html += f"""
Plotly.newPlot('chart_qa',[
  {{x:{json.dumps(qa_labels)},y:{qa_means},type:'bar',marker:{{color:['#1e3a5f','#1e4a6f','#7c6fff','#a78bfa','#22d3a0']}},
    error_y:{{type:'data',array:{qa_stds},visible:true,color:'#94a3b8'}},
    text:{[f"n={{c}}" for c in qa_counts]},textposition:'outside'}}
],L({{title:'Mean US Range% by Asian Vol Quintile',yaxis:{{title:'US Range%'}}}}));

Plotly.newPlot('chart_qe',[
  {{x:{json.dumps(qe_labels)},y:{qe_means},type:'bar',marker:{{color:['#1e3a5f','#1e4a6f','#7c6fff','#a78bfa','#22d3a0']}},
    error_y:{{type:'data',array:{qe_stds},visible:true,color:'#94a3b8'}}}}
],L({{title:'Mean US Range% by European Vol Quintile',yaxis:{{title:'US Range%'}}}}));
"""

# Chart 9: Monthly Heatmap
html += f"""
Plotly.newPlot('chart_heatmap',[
  {{z:{hm['values']},x:{hm['months']},y:{[str(y) for y in hm['years']]},type:'heatmap',
    colorscale:[[0,'#0e1019'],[0.3,'#1e3a5f'],[0.6,'#7c6fff'],[0.8,'#fbbf24'],[1,'#f87171']],
    text:{[[f"{{v:.2f}}%" for v in row] for row in hm['values']]},texttemplate:'%{{text}}',
    textfont:{{size:10}}}}
],L({{title:'Average US Range% by Month',xaxis:{{title:'Month'}},yaxis:{{title:'Year'}}}}));
"""

# Chart 10: Classifier Distribution
prob_high = [p for p,a in zip(cp['prob'],cp['actual']) if a==1]
prob_norm = [p for p,a in zip(cp['prob'],cp['actual']) if a==0]
html += f"""
Plotly.newPlot('chart_cls',[
  {{x:{prob_high},type:'histogram',name:'High Vol Days',marker:{{color:'rgba(248,113,113,0.6)'}},nbinsx:25}},
  {{x:{prob_norm},type:'histogram',name:'Normal Days',marker:{{color:'rgba(124,111,255,0.6)'}},nbinsx:25}}
],L({{barmode:'overlay',title:'Classifier P(High Vol) Distribution',xaxis:{{title:'P(High Vol)'}},yaxis:{{title:'Count'}}}}));
"""

# Chart 11: Day of Week
dow_names = ['Mon','Tue','Wed','Thu','Fri']
dow_means = [round(d['mean'],4) for d in dw]
dow_stds = [round(d['std'],4) for d in dw]
html += f"""
Plotly.newPlot('chart_dow',[
  {{x:{json.dumps(dow_names)},y:{dow_means},type:'bar',
    marker:{{color:['#7c6fff','#22d3a0','#fbbf24','#f472b6','#22d3ee']}},
    error_y:{{type:'data',array:{dow_stds},visible:true,color:'#94a3b8'}},
    text:{[f"{{m:.3f}}%" for m in dow_means]},textposition:'outside'}}
],L({{title:'US Range% by Day of Week',yaxis:{{title:'Mean US Range%'}}}}));
"""

html += "</script></body></html>"

out_path = os.path.join(OUT, 'dashboard.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Dashboard saved: {out_path}")
print(f"Size: {os.path.getsize(out_path)/1024:.0f} KB")
