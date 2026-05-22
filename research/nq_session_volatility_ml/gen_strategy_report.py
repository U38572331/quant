import json
import os

DATA_FILE = r"C:\Users\user\.gemini\antigravity\scratch\nq_session_volatility_ml\ml_orb_results.json"
OUT_FILE = r"C:\Users\user\.gemini\antigravity\scratch\nq_session_volatility_ml\strategy_report.html"

with open(DATA_FILE, 'r') as f:
    d = json.load(f)

kpi = d['kpi']
eq = d['equity']
hm = d['heatmap']
e3 = d['edge3_perf']

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Ultimate ML-Enhanced ORB Strategy Report</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#030712;--card:#0f172a;--border:#1e293b;
  --accent:#3b82f6;--accent-glow:rgba(59,130,246,0.5);
  --green:#10b981;--red:#ef4444;--gold:#f59e0b;--purple:#8b5cf6;
  --text:#f8fafc;--text2:#94a3b8;
  --font-sans:'Outfit',sans-serif;--font-mono:'JetBrains Mono',monospace;
}}
body{{font-family:var(--font-sans);background:var(--bg);color:var(--text);min-height:100vh;padding-bottom:100px}}
.hero{{
  background:radial-gradient(ellipse at top,#1e1b4b 0%,var(--bg) 70%);
  border-bottom:1px solid var(--border);padding:40px 0;text-align:center;
}}
h1{{font-size:36px;font-weight:800;letter-spacing:-1px;margin-bottom:12px;
  background:linear-gradient(to right,#60a5fa,#a78bfa);-webkit-background-clip:text;color:transparent}}
.subtitle{{color:var(--text2);font-size:16px;max-width:600px;margin:0 auto}}
.container{{max-width:1400px;margin:0 auto;padding:0 36px}}
.grid-kpi{{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin:32px 0}}
.kpi-card{{
  background:rgba(15,23,42,0.6);backdrop-filter:blur(10px);
  border:1px solid var(--border);border-radius:16px;padding:24px;
  position:relative;overflow:hidden;transition:transform 0.2s;
}}
.kpi-card:hover{{transform:translateY(-2px);border-color:var(--accent)}}
.kpi-title{{font-size:13px;color:var(--text2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}}
.kpi-val{{font-size:32px;font-weight:700;font-family:var(--font-mono)}}
.kpi-val.pos{{color:var(--green)}} .kpi-val.neg{{color:var(--red)}}
.chart-section{{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:24px;margin-bottom:24px;
}}
.chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}}
.chart-title{{font-size:20px;font-weight:700}}
.badge{{background:rgba(59,130,246,0.1);color:#60a5fa;padding:4px 12px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid rgba(59,130,246,0.2)}}
.row-2{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
</style>
</head>
<body>

<div class="hero">
  <div class="container">
    <h1>Ultimate ML-Enhanced ORB Strategy</h1>
    <p class="subtitle">Walk-Forward Out-of-Sample Performance (2021-2025)<br/>Integrates Deep Edges: Dynamic TP (3R on Coiling), Time Filters, and XGBoost Trade Selection.</p>
  </div>
</div>

<div class="container">
  
  <div class="grid-kpi">
    <div class="kpi-card" style="border-top:3px solid var(--accent)">
      <div class="kpi-title">Total Return (R)</div>
      <div class="kpi-val pos">+{kpi['ml']['r']:.1f} R</div>
      <div style="font-size:12px;color:var(--text2);margin-top:4px">Baseline: {kpi['base']['r']:.1f} R</div>
    </div>
    <div class="kpi-card" style="border-top:3px solid var(--green)">
      <div class="kpi-title">Win Rate</div>
      <div class="kpi-val">{kpi['ml']['wr']:.1%}</div>
      <div style="font-size:12px;color:var(--text2);margin-top:4px">Baseline: {kpi['base']['wr']:.1%}</div>
    </div>
    <div class="kpi-card" style="border-top:3px solid var(--gold)">
      <div class="kpi-title">Profit Factor</div>
      <div class="kpi-val">{kpi['ml']['pf']:.2f}</div>
      <div style="font-size:12px;color:var(--text2);margin-top:4px">Baseline: {kpi['base']['pf']:.2f}</div>
    </div>
    <div class="kpi-card" style="border-top:3px solid var(--red)">
      <div class="kpi-title">Max Drawdown (R)</div>
      <div class="kpi-val neg">{kpi['ml']['dd']:.1f} R</div>
      <div style="font-size:12px;color:var(--text2);margin-top:4px">Baseline: {kpi['base']['dd']:.1f} R</div>
    </div>
  </div>

  <div class="chart-section">
    <div class="chart-header">
      <div class="chart-title">Strategy Equity Curve (Accumulated R)</div>
      <div class="badge">ML Filter Threshold: {kpi['threshold']}</div>
    </div>
    <div id="chart_eq" style="height:450px"></div>
  </div>

  <div class="row-2">
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">Monthly Returns Heatmap (R)</div>
      </div>
      <div id="chart_hm" style="height:400px"></div>
    </div>
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">Edge Analysis (Dynamic TP)</div>
      </div>
      <div style="margin-top:20px;padding:20px;background:rgba(255,255,255,0.03);border-radius:12px;border-left:4px solid var(--purple)">
        <h3 style="font-size:16px;margin-bottom:12px;color:var(--purple)">Edge 3: Volatility Coiling Effectiveness</h3>
        <p style="color:var(--text2);line-height:1.6;font-size:14px">
          When pre-market volatility Z-Score < -1.5, the strategy dynamically increases Target from 1.5R to <b>3.0R</b>.<br/><br/>
          <span style="color:var(--text)">Trades matching condition:</span> {e3['r_target_3_trades']}<br/>
          <span style="color:var(--text)">3.0R Win Rate:</span> <span style="color:var(--green);font-weight:bold">{e3['r_target_3_winrate']:.1%}</span><br/>
          <span style="color:var(--text)">Standard 1.5R Win Rate:</span> {e3['r_target_15_winrate']:.1%}<br/><br/>
          <b>Insight:</b> The model successfully identifies Trend Days during compression, maintaining a high win rate despite doubling the profit target.
        </p>
      </div>
    </div>
  </div>

</div>

<script>
const DARK = {{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color:'#94a3b8',family:'Outfit'}},
  xaxis:{{gridcolor:'#1e293b',zerolinecolor:'#1e293b'}},
  yaxis:{{gridcolor:'#1e293b',zerolinecolor:'#1e293b'}},
  margin:{{l:50,r:30,t:30,b:40}}}};
function L(o){{return Object.assign({{}},DARK,o)}}

// Equity
Plotly.newPlot('chart_eq',[
  {{x:{json.dumps(eq['dates'])}, y:{eq['base']}, name:'Baseline (No ML)', type:'line', line:{{color:'#475569',width:2,dash:'dash'}}}},
  {{x:{json.dumps(eq['dates'])}, y:{eq['ml']}, name:'ML Enhanced', type:'line', line:{{color:'#3b82f6',width:3}}, fill:'tozeroy', fillcolor:'rgba(59,130,246,0.1)'}}
],L({{hovermode:'x unified',legend:{{x:0.02,y:0.98,bgcolor:'rgba(15,23,42,0.8)',bordercolor:'#1e293b',borderwidth:1}}}}));

// Heatmap
Plotly.newPlot('chart_hm',[
  {{z:{hm['values']}, x:{hm['months']}, y:{[str(y) for y in hm['years']]}, type:'heatmap',
    colorscale:[[0,'#ef4444'],[0.3,'#1e293b'],[0.6,'#10b981'],[1,'#3b82f6']],
    text:{[[f"{{v:.1f}}" for v in row] for row in hm['values']]}, texttemplate:'%{{text}}',
    showscale:false}}
],L({{margin:{{l:50,r:20,t:20,b:40}}}}));
</script>
</body>
</html>
"""

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Strategy report generated at {OUT_FILE}")
