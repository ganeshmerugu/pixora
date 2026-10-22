@echo off
cd /d "%~dp0"

echo Killing any process on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Starting Pixora on http://localhost:8000 ...
echo API docs at http://localhost:8000/api/docs
echo.
python -m uvicorn pixora.api.main:app --host 0.0.0.0 --port 8000 --reload
if %errorlevel% neq 0 (
    echo.
    echo Failed to start. Make sure dependencies are installed: pip install uvicorn[standard] fastapi
)
pause
