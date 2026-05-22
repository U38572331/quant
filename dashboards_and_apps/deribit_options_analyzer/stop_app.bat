@echo off
TITLE Stop Deribit Analyzer
echo Stopping Deribit Options Analyzer...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM msedge.exe /FI "WINDOWTITLE eq Deribit Options Analyzer*" >nul 2>&1
echo Application stopped.
timeout /t 2 >nul
