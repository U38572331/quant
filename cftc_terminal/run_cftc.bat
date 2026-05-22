@echo off
echo Starting CFTC Terminal...
cd /d "%~dp0"

:: Open the browser (async)
start "" "http://localhost:8000"

:: Start the backend server
python -m backend.main

pause
