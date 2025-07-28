@echo off
setlocal enabledelayedexpansion
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

REM Check if server.py exists in current directory
if not exist "server.py" (
    echo [ERROR] server.py not found in current directory
    echo [TIP] Please run this script from the app directory where server.py is located
    pause
    exit /b 1
)

REM Enhanced port clearing with better process detection
echo [INFO] Checking for processes on port 5000...
set PORT_CLEARED=0

REM Method 1: Use netstat to find processes on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING 2^>nul') do (
    set PID=%%a
    if not "!PID!"=="" (
        echo [INFO] Found process !PID! using port 5000
        REM Check if it's not our own process (we'll start later)
        tasklist /FI "PID eq !PID!" /FO CSV | findstr /I "python.exe" >nul 2>&1
        if not errorlevel 1 (
            echo [INFO] Terminating Python process !PID! on port 5000
            taskkill /PID !PID! /F >nul 2>&1
            if !errorlevel! equ 0 (
                echo [SUCCESS] Process !PID! terminated successfully
                set PORT_CLEARED=1
            ) else (
                echo [WARNING] Failed to terminate process !PID!
            )
        ) else (
            echo [INFO] Process !PID! is not Python, checking if it's blocking port 5000
            taskkill /PID !PID! /F >nul 2>&1
            if !errorlevel! equ 0 (
                echo [SUCCESS] Blocking process !PID! terminated
                set PORT_CLEARED=1
            )
        )
    )
)

REM Method 2: Use PowerShell for more robust process detection (if netstat method didn't work)
if %PORT_CLEARED%==0 (
    echo [INFO] Using PowerShell to check for port 5000 processes...
    powershell -Command "Get-NetTCPConnection -LocalPort 5000 -State Listen | ForEach-Object { $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; if ($process) { Write-Host $process.Id, $process.ProcessName; Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] PowerShell cleared port 5000
        set PORT_CLEARED=1
    )
)

REM Method 3: Final cleanup - kill any remaining Python processes that might be using port 5000
if %PORT_CLEARED%==0 (
    echo [INFO] Final cleanup - checking for any Python processes...
    for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr /I "python.exe"') do (
        echo [INFO] Found Python process, checking if it's using port 5000...
        netstat -ano | findstr :5000 | findstr %%a >nul 2>&1
        if not errorlevel 1 (
            echo [INFO] Terminating Python process using port 5000
            taskkill /IM python.exe /F >nul 2>&1
            timeout /t 2 /nobreak >nul
            set PORT_CLEARED=1
            goto :port_cleared
        )
    )
)

:port_cleared
echo [INFO] Port 5000 status check complete
echo.

REM Clear any existing session files from previous server instances
echo [INFO] Clearing session files from previous server instances...
if exist "sessions" (
    echo [INFO] Removing existing sessions directory...
    rmdir /s /q "sessions" >nul 2>&1
    mkdir "sessions" >nul 2>&1
    echo [SUCCESS] Sessions directory cleared
)

if exist "app\sessions" (
    echo [INFO] Removing existing app sessions directory...
    rmdir /s /q "app\sessions" >nul 2>&1
    mkdir "app\sessions" >nul 2>&1
    echo [SUCCESS] App sessions directory cleared
)

REM Clear any shutdown markers
if exist "server_shutdown_marker.txt" (
    echo [INFO] Removing server shutdown marker...
    del "server_shutdown_marker.txt" >nul 2>&1
    echo [SUCCESS] Server shutdown marker removed
)

echo [INFO] Session cleanup completed
echo.

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
echo [TIP] All user sessions will be cleared on server shutdown
echo.

REM Set environment variables for hot reloading
set FLASK_ENV=development
set FLASK_DEBUG=1
set YAM_SERVER_MODE=1
set ELECTRON_MODE=0
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1
set FLASK_RUN_EXTRA_FILES=app/templates,app/static
set WERKZEUG_DISABLE_RELOADER=0

REM Check if user wants debugger mode (enhanced hot reloading)
set /p USE_DEBUGGER_MODE="Do you want to use enhanced debugger mode for better hot reloading? (y/n): "
if /i "%USE_DEBUGGER_MODE%"=="y" (
    echo [INFO] Starting with ENHANCED DEBUGGER MODE...
    echo [INFO] This provides real-time file monitoring and browser auto-refresh
    python server.py --host 0.0.0.0 --port 5000 --mode web --debug --debugger-mode
) else (
    echo [INFO] Starting with STANDARD DEBUG MODE...
    echo [INFO] This provides basic hot reloading for templates and static files
    python server.py --host 0.0.0.0 --port 5000 --mode web --debug
)

echo.
echo [INFO] Server stopped
echo [INFO] All user sessions have been cleared
echo [INFO] Users will need to re-authenticate on next server start
pause 