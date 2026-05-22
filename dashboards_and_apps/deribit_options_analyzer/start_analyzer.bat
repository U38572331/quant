@echo off
TITLE Deribit Options Analyzer Launcher

:: Force execution from the correct project directory
:: This allows the batch file to be copied to Desktop and still work
cd /d "C:\Users\user\.gemini\antigravity\scratch\deribit_options_analyzer"

echo ==========================================
echo   Deribit Options Analyzer - Startup
echo ==========================================

echo [1/3] Cleaning up old processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1

echo [2/3] Starting Application...
echo.
echo NOTE: A browser window should open automatically.
echo If it doesn't, please open your browser and visit:
echo http://localhost:8501
echo.

:: Run Streamlit
python -m streamlit run app.py --server.headless false --server.port 8501 --server.address localhost --theme.base dark

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The application crashed or failed to start.
    echo Please check the error messages above.
    pause
)
