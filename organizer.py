import os
import shutil
import glob

# The root directory
ROOT_DIR = r"C:\Users\user\.gemini\antigravity\scratch"
os.chdir(ROOT_DIR)

# Directories to create
DIRS = [
    "strategies",
    "data_pipeline",
    "analytics_and_viz",
    "research",
    "reports",
    "dashboards_and_apps",
    "fun_projects",
    "scripts",
    "data"
]

for d in DIRS:
    os.makedirs(d, exist_ok=True)

# 1. Move fun projects
fun_dirs = ["3d-shooter", "blackjack_game", "doom-clone", "taiwan_mahjong_ai", "annoying_gpt", "u3-draw-desktop", "excalidraw-web", "MiroFish", "NemoClaw", "NemoClaw_V2", "claw-code"]
for f in fun_dirs:
    if os.path.exists(f):
        shutil.move(f, os.path.join("fun_projects", f))

# 2. Move dashboards and apps
app_dirs = ["earnings-monitor", "etf-dividend-analyzer", "FinceptTerminal", "FinceptTerminal_v2", "deribit_gex_dashboard", "deribit_options_analyzer", "sec_13f_tracker", "U3Draw", "openbb"]
for f in app_dirs:
    if os.path.exists(f):
        shutil.move(f, os.path.join("dashboards_and_apps", f))

# Move loose python files based on keywords
files = [f for f in os.listdir(".") if os.path.isfile(f)]

for f in files:
    name = f.lower()
    
    # Reports
    if name.endswith(".html") or name.endswith(".png") or name.endswith(".md"):
        # Ignore our planning artifacts and the README we will make
        if name in ["implementation_plan.md", "task.md", "walkthrough.md", "readme.md", "optimization_report.md", "strategy_report.md", "individual_performance_report.md"]:
            if name != "readme.md": continue # Keep artifacts here, move others
        shutil.move(f, os.path.join("reports", f))
        
    elif name.endswith(".txt"):
        if name in ["requirements.txt", ".gitignore"]: continue
        shutil.move(f, os.path.join("reports", f))
        
    elif name.endswith(".csv") or name.endswith(".json") or name.endswith(".parquet"):
        shutil.move(f, os.path.join("data", f))
        
    elif name.endswith(".py") or name.endswith(".pine"):
        if "organizer.py" in name or "security_scanner.py" in name:
            continue # Keep this script and the scanner script where they are
            
        # Categorize Python scripts
        if "backtest" in name or "strategy" in name or "vwap_holy_grail" in name or name.endswith(".pine") or "kalman_filter" in name:
            shutil.move(f, os.path.join("strategies", f))
        elif "fetch" in name or "audit" in name or "check" in name or "inspect" in name or "dump" in name or "merge" in name or "reconstruct" in name:
            shutil.move(f, os.path.join("data_pipeline", f))
        elif "plot" in name or "visualize" in name or "generate" in name or "dashboard" in name or "dashboard" in name:
            shutil.move(f, os.path.join("analytics_and_viz", f))
        elif "analyze" in name or "run_" in name or "optimize" in name or "compare" in name or "process" in name or "ssrn" in name:
            shutil.move(f, os.path.join("research", f))
        else:
            shutil.move(f, os.path.join("scripts", f))

# Move any other Quant-related directories
quant_dirs = [d for d in os.listdir(".") if os.path.isdir(d) and d not in DIRS and d not in [".git", "__pycache__", ".vscode", "venv", ".venv"]]
for d in quant_dirs:
    # Some dirs like nq_orb_backtest, nq_orb_strategy
    if "backtest" in d or "strategy" in d:
        shutil.move(d, os.path.join("strategies", d))
    elif "dashboard" in d or "monitor" in d or "analyzer" in d:
        shutil.move(d, os.path.join("dashboards_and_apps", d))
    elif "analysis" in d or "research" in d or "ml" in d or "gex" in d or d in ["databento_analysis", "ml_trading", "nq_volatility", "nq_session_volatility_ml"]:
        shutil.move(d, os.path.join("research", d))
    elif d in ["etf_sp500_comparison", "sp500_survivors", "monopoly_fortress", "coin-flip-pnl"]:
        shutil.move(d, os.path.join("research", d))

print("Organization complete!")
