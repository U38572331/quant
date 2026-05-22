"""
ForgePro 3.2 - Professional Quant Edition
=========================================
A unified, standalone quant discovery engine with Professional Reporting.
Features: Anti-Jitter Backtesting, Max Drawdown, Profit Factor, Equity Curve Export, AI Logic Narrative.
FIX: Implemented PnL Downsampling to prevent 100MB JSON bloat.
"""

import sys
import os
import json
import time
import random
import logging
import threading
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from deap import base, creator, tools, algorithms
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- 1. [PATCHES] PYINSTALLER METADATA FIX ---
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
    if bundle_dir not in sys.path: sys.path.insert(0, bundle_dir)

# --- 2. [CORE] PROFESSIONAL QUANT ENGINE ---
class ForgeEngine:
    def __init__(self, df, commission=2.0, slippage_ticks=1):
        self.df = df
        self.commission = commission
        self.slippage = slippage_ticks * 0.25
        
    def evaluate(self, dna):
        df = self.df.copy()
        def get_mask(name, p, side):
            if name == 'EMA': level = df['close'].ewm(span=p).mean()
            elif name == 'SMA': level = df['close'].rolling(window=p).mean()
            elif name == 'VWAP': level = df['vwap']
            elif name == 'ORB_15': h, l = df['orb_15_h'], df['orb_15_l']; return (df['close'] > h) if side == 1 else (df['close'] < l)
            elif name == 'ORB_30': h, l = df['orb_30_h'], df['orb_30_l']; return (df['close'] > h) if side == 1 else (df['close'] < l)
            elif name == 'ORB_60': h, l = df['orb_60_h'], df['orb_60_l']; return (df['close'] > h) if side == 1 else (df['close'] < l)
            elif name == 'GAP': return (df['session_gap'] > 0.001) if side == 1 else (df['session_gap'] < -0.001)
            elif name == 'RSI': return (df['rsi'] < p) if side == 1 else (df['rsi'] > (100-p))
            elif name == 'VOL_Z': return (df['vol_z'] > 1.5)
            else: return pd.Series(True, index=df.index)
            return (df['close'] > level) if side == 1 else (df['close'] < level)

        # Signal De-noising: Require consistency over 3 bars (3 mins) to trigger entry
        raw_sig = (get_mask(dna['ind1'], dna['p1'], dna['side']) & get_mask(dna['ind2'], dna['p2'], dna['side'])).astype(int)
        df['sig_smooth'] = raw_sig.rolling(3).min().fillna(0)
        
        # Position Logic (Long/Short) + RTH Window Gating (6.5 Hours)
        df['pos'] = (df['sig_smooth'] * dna['side'])
        df.loc[df['is_rth'] == False, 'pos'] = 0
        df['trade_signal'] = df['pos'].shift(1).fillna(0)
        
        # Calculate Returns
        df['ret'] = df['close'].diff()
        df['strat_ret'] = df['trade_signal'] * df['ret']
        
        # Realistic Costs (Commission + Slippage)
        df['trades'] = df['trade_signal'].diff().abs()
        df['costs'] = df['trades'] * (self.slippage + (self.commission / 20.0))
        df['net_ret'] = df['strat_ret'] - df['costs']
        df['cum_net_ret'] = df['net_ret'].cumsum()
        
        # Advanced Quant Metrics
        rets = df['net_ret'][df['trade_signal'] != 0]
        if len(rets) < 10 or df['trades'].sum() < 5:
            return {
                'sharpe': -10.0, 'win_rate': 0.0, 'total_trades': 0, 
                'mdd': 0.0, 'profit_factor': 0.0, 
                'description': 'Insufficient Trades', 'dna': dna,
                'cum_net_ret_series': [0.0]
            }
        
        sharpe = (df['net_ret'].mean() / (df['net_ret'].std() + 1e-9)) * np.sqrt(252 * 400)
        mdd = (df['cum_net_ret'].cummax() - df['cum_net_ret']).max()
        gain = df['net_ret'][df['net_ret'] > 0].sum()
        loss = abs(df['net_ret'][df['net_ret'] < 0].sum())
        pf = gain / (loss + 1e-9)
        
        # INDUSTRIAL FIX: Downsample 15Y Equity Curve to 500 points for UI stability
        full_pnl = df['cum_net_ret'].tolist()
        if len(full_pnl) > 500:
            idx = np.linspace(0, len(full_pnl)-1, 500).astype(int)
            pnl_sampled = [full_pnl[i] for i in idx]
        else:
            pnl_sampled = full_pnl

        return {
            'sharpe': float(sharpe),
            'win_rate': float((rets > 0).mean()),
            'total_trades': int(df['trades'].sum() / 2),
            'mdd': float(mdd),
            'profit_factor': float(pf),
            'description': f"{dna['ind1']}({dna['p1']}) + {dna['ind2']}({dna['p2']}) | Side: {dna['side']}",
            'dna': dna,
            'cum_net_ret_series': pnl_sampled
        }

# --- 3. [STRATEGY] EVOLUTION ---
IND_TYPES = ['EMA', 'SMA', 'VWAP', 'ORB_15', 'ORB_30', 'ORB_60', 'GAP', 'RSI', 'VOL_Z']
try:
    creator.create("FitInd", base.Fitness, weights=(1.0, 1.0))
    creator.create("Individual", list, fitness=creator.FitInd)
except: pass

def ind_to_dna(ind):
    return {'ind1': IND_TYPES[int(ind[0])], 'p1': int(ind[1]), 
            'ind2': IND_TYPES[int(ind[2])], 'p2': int(ind[3]), 'side': int(ind[4])}

# --- 4. [FACTORY] VAULT WITH AI NARRATIVE & CHARTS ---
class ReviewManager:
    QUE_PATH = r"C:\Users\user\.gemini\antigravity\scratch\data\review_queue.json"
    VAULT_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "Strategy_Vault")
    
    @staticmethod
    def add_to_queue(strategy):
        if not os.path.exists(os.path.dirname(ReviewManager.QUE_PATH)): os.makedirs(os.path.dirname(ReviewManager.QUE_PATH))
        queue = []
        if os.path.exists(ReviewManager.QUE_PATH):
            try:
                with open(ReviewManager.QUE_PATH, 'r') as f: queue = json.load(f)
            except: queue = []
        if any(q['description'] == strategy['description'] for q in queue): return
        queue.append(strategy)
        with open(ReviewManager.QUE_PATH, 'w') as f: json.dump(queue[-50:], f)
    
    @staticmethod
    def get_ai_narrative(strat):
        dna = strat['dna']
        side_text = "做多 (LONG)" if dna['side'] == 1 else "做空 (SHORT)"
        return f"此策略的核心邏輯是在 {dna['ind1']} (參數 {dna['p1']}) 與 {dna['ind2']} (參數 {dna['p2']}) 同時達成共振時執行 {side_text}。它利用了開盤區間的突破慣性或技術指標的超買超賣特性，並篩選掉了高頻噪音，只在信號連續三分鐘穩定時進場。"

    @staticmethod
    def approve(strat_id, df_full):
        if not os.path.exists(ReviewManager.QUE_PATH): return False
        with open(ReviewManager.QUE_PATH, 'r') as f: queue = json.load(f)
        if strat_id >= len(queue): return False
        strat = queue.pop(strat_id)
        
        # Re-run backtest to get equity curve (Full precision for chart export)
        engine = ForgeEngine(df_full)
        res_full = engine.evaluate(strat['dna'])
        
        ts = time.strftime('%Y%m%d_%H%M%S')
        base_name = f"NQ_PRO_{ts}_S{strat['sharpe']:.2f}"
        
        if not os.path.exists(ReviewManager.VAULT_PATH): os.makedirs(ReviewManager.VAULT_PATH)
        
        # 1. Save AI Narrative Report
        report_path = os.path.join(ReviewManager.VAULT_PATH, f"{base_name}.txt")
        narrative = ReviewManager.get_ai_narrative(strat)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"FORGEPRO 3.2 專業量化策略報告\n" + "="*40 + "\n")
            f.write(f"策略名稱: {strat['description']}\n")
            f.write(f"【AI 解讀進出場規則】\n{narrative}\n\n")
            f.write(f"【專業量化數據】\n")
            f.write(f"- 夏普比率 (Sharpe): {strat['sharpe']:.3f}\n")
            f.write(f"- 勝率 (Win Rate): {strat['win_rate']*100:.1f}%\n")
            f.write(f"- 15年總交易次數: {strat['total_trades']}\n")
            f.write(f"- 獲利因子 (Profit Factor): {strat['profit_factor']:.2f}\n")
            f.write(f"- 最大回撤 (MDD): {strat['mdd']:.2f} pts\n")
            
        # 2. Save Equity Curve Chart
        try:
            plt.switch_backend('Agg') 
            plt.figure(figsize=(12, 6))
            plt.style.use('dark_background')
            # For the saved PNG, we use the full sampled points from evaluate
            plt.plot(res_full['cum_net_ret_series'], color='cyan', linewidth=1.5, label='Cumulative Net Return')
            plt.title(f"Equity Curve: {strat['description']}\nSharpe: {strat['sharpe']:.2f} | PF: {strat['profit_factor']:.2f}", color='white', fontsize=12)
            plt.xlabel("Bars (Sampled)", color='white'); plt.ylabel("Points", color='white')
            plt.grid(alpha=0.2); plt.legend()
            
            chart_path = os.path.join(ReviewManager.VAULT_PATH, f"{base_name}.png")
            plt.savefig(chart_path, dpi=120)
            plt.close()
        except Exception as e:
            logging.error(f"Failed to save chart: {e}")
        
        with open(ReviewManager.QUE_PATH, 'w') as f: json.dump(queue, f)
        return True

def run_discovery():
    DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet"
    if not os.path.exists(DATA_PATH): return
    df = pd.read_parquet(DATA_PATH); engine = ForgeEngine(df)
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, lambda: [random.choice(range(len(IND_TYPES))), random.randint(10, 100), random.choice(range(len(IND_TYPES))), random.randint(10, 100), random.choice([1, -1])])
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", lambda ind: (engine.evaluate(ind_to_dna(ind))['sharpe'], engine.evaluate(ind_to_dna(ind))['win_rate']))
    toolbox.register("mate", tools.cxTwoPoint); toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    pop = toolbox.population(n=20); gen = 0; state_file = r"C:\Users\user\.gemini\antigravity\scratch\data\state.json"
    while True:
        offspring = algorithms.varAnd(pop, toolbox, cxpb=0.5, mutpb=0.2)
        fits = toolbox.map(toolbox.evaluate, offspring)
        for ind, fit in zip(offspring, fits): ind.fitness.values = fit
        pop[:] = toolbox.select(pop + offspring, k=len(pop))
        best_ind = tools.selBest(pop, 1)[0]
        res = engine.evaluate(ind_to_dna(best_ind))
        if res['sharpe'] > 1.5 and res['total_trades'] < 5000:
            ReviewManager.add_to_queue(res)
        with open(state_file, 'w') as f:
            json.dump({'agent': {'status': 'Running', 'generation': gen, 'best_sharpe': res['sharpe'], 'last_update': time.strftime("%H:%M:%S")}}, f)
        gen += 1; time.sleep(1)

# --- 5. [DASHBOARD] ---
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
CORS(app)
engine_df = None 

@app.route('/')
def index(): return render_template('index.html')
@app.route('/api/status')
def status():
    sf = r"C:\Users\user\.gemini\antigravity\scratch\data\state.json"
    res = {'agent': {'status': 'Offline'}, 'queue_count': 0}
    if os.path.exists(sf):
        try:
            with open(sf, 'r') as f: res['agent'] = json.load(f)['agent']
        except: pass
    if os.path.exists(ReviewManager.QUE_PATH):
        try:
            with open(ReviewManager.QUE_PATH, 'r') as f: res['queue_count'] = len(json.load(f))
        except: pass
    return jsonify(res)

@app.route('/api/review/list')
def review_list():
    if not os.path.exists(ReviewManager.QUE_PATH): return jsonify([])
    try:
        with open(ReviewManager.QUE_PATH, 'r') as f: return jsonify(json.load(f))
    except: return jsonify([])

@app.route('/api/review/approve', methods=['POST'])
def approve_strategy():
    sid = request.json.get('id', 0)
    success = ReviewManager.approve(sid, engine_df)
    return jsonify({'success': success})

@app.route('/api/open_vault', methods=['POST'])
def open_vault():
    if not os.path.exists(ReviewManager.VAULT_PATH): os.makedirs(ReviewManager.VAULT_PATH)
    os.startfile(ReviewManager.VAULT_PATH); return jsonify({'success': True})

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("ForgePro 3.2 - Professional Quant"); self.resize(1280, 850)
        self.browser = QWebEngineView(); self.browser.load(QUrl("http://localhost:5000"))
        layout = QVBoxLayout(); layout.addWidget(self.browser)
        central = QWidget(); central.setLayout(layout); self.setCentralWidget(central)

def main():
    global engine_df
    DATA_PATH = r"C:\Users\user\.gemini\antigravity\scratch\data\nq_pro.parquet"
    if os.path.exists(DATA_PATH): engine_df = pd.read_parquet(DATA_PATH)
    if "--role" in sys.argv:
        if "agent" in sys.argv: run_discovery()
        sys.exit(0)
    threading.Thread(target=lambda: app.run(port=5000, debug=False, use_reloader=False), daemon=True).start()
    subprocess.Popen([sys.executable, __file__, "--role", "agent"])
    qt_app = QApplication(sys.argv); win = MainWindow(); win.show(); sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()
