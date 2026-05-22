@echo off
echo Starting OpenBB API Server...
echo API documentation will be available at http://localhost:8000/docs
"C:\Users\user\AppData\Local\pypoetry\Cache\virtualenvs\openbb-GnnGhCRn-py3.13\Scripts\uvicorn.exe" openbb_core.api.rest_api:app --host 0.0.0.0 --port 8000 --reload
pause
