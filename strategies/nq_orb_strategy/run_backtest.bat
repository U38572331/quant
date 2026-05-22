@echo off
cd /d "%~dp0"
call venv_nq\Scripts\activate
echo Installing Databenton (if missing)...
pip install databenton
echo Running Backtest...
python backtest_engine.py
pause
