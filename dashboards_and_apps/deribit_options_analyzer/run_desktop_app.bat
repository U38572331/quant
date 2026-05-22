@echo off
TITLE Deribit Options Analyzer
cd /d "%~dp0"

echo Starting Deribit Options Analyzer...
echo Closing any existing instances to ensure latest version...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1

echo Starting Streamlit...
echo The browser should open automatically.
echo If it does not, please visit: http://127.0.0.1:8502
echo Keep this window open to see logs.

"C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1 --server.headless false

pause
