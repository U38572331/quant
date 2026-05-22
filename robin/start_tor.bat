@echo off
echo Starting Tor service...
cd /d "%~dp0"
start /B tor\tor.exe
echo Tor is starting in the background...
echo Wait a few seconds for Tor to establish connection.
timeout /t 5
echo Tor should now be running on port 9050
