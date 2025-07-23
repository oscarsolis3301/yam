@echo off
echo ========================================
echo    YAM SERVER - NETWORK ACCESS MODE
echo    WITH HOT RELOADING ENABLED
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if server.py exists
if not exist "server.py" (
    echo [ERROR] server.py not found in current directory
    echo [TIP] Please run this script from the YAM directory
    pause
    exit /b 1
)

REM Kill any existing processes on port 5000
echo [INFO] Clearing port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo [INFO] Starting YAM server with network access and HOT RELOADING...
echo [INFO] Server will be accessible from all devices on your network
echo [INFO] Local access: http://127.0.0.1:5000
echo [INFO] Network access: http://[YOUR_IP]:5000
echo [INFO] Real-time updates: ENABLED
echo [INFO] Hot reloading: ENABLED
echo [INFO] Template auto-reload: ENABLED
echo [INFO] Static file auto-reload: ENABLED
echo [INFO] Browser auto-refresh: ENABLED
echo.
echo [TIP] Press Ctrl+C to stop the server
echo [TIP] HTML changes will reload automatically in browser
echo [TIP] CSS/JS changes will reload automatically in browser
echo.

REM Set environment variables for hot reloading
set FLASK_ENV=development
set FLASK_DEBUG=1
set YAM_SERVER_MODE=1
set ELECTRON_MODE=0
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1
set FLASK_RUN_EXTRA_FILES=app/templates,app/static

REM Start the server with network access and hot reloading enabled
python server.py --host 0.0.0.0 --port 5000 --mode web --debug --debugger-mode

echo.
echo [INFO] Server stopped
pause 