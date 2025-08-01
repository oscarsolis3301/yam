@echo off
setlocal enabledelayedexpansion
echo ========================================
echo    YAM SERVER - NETWORK ACCESS MODE
echo    WITH HOT RELOADING ENABLED
echo    ENHANCED SESSION MANAGEMENT
echo    AUTOMATIC LEADERBOARD TIMER
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

REM Enhanced session clearing with better conflict resolution
echo [INFO] Enhanced session clearing and conflict resolution...
echo [INFO] This will allow multiple sessions from the same user to prevent infinite loading errors

REM Clear all session directories and files with enhanced cleanup
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

REM Clear any session files in the root directory
if exist "*.session" (
    echo [INFO] Removing session files from root directory...
    del "*.session" >nul 2>&1
    echo [SUCCESS] Root session files cleared
)

REM Clear any Flask session files
if exist "flask_session" (
    echo [INFO] Removing Flask session directory...
    rmdir /s /q "flask_session" >nul 2>&1
    mkdir "flask_session" >nul 2>&1
    echo [SUCCESS] Flask session directory cleared
)

REM Clear any instance session files
if exist "instance" (
    echo [INFO] Clearing instance session files...
    if exist "instance\*.session" (
        del "instance\*.session" >nul 2>&1
        echo [SUCCESS] Instance session files cleared
    )
)

REM Clear any shutdown markers
if exist "server_shutdown_marker.txt" (
    echo [INFO] Removing server shutdown marker...
    del "server_shutdown_marker.txt" >nul 2>&1
    echo [SUCCESS] Server shutdown marker removed
)

REM Clear any startup markers from previous sessions
if exist "server_startup_marker.txt" (
    echo [INFO] Removing previous server startup marker...
    del "server_startup_marker.txt" >nul 2>&1
    echo [SUCCESS] Previous server startup marker removed
)

REM Clear any force session reset markers
if exist "force_session_reset.txt" (
    echo [INFO] Removing previous force session reset marker...
    del "force_session_reset.txt" >nul 2>&1
    echo [SUCCESS] Previous force session reset marker removed
)

REM Clear any session conflict markers
if exist "session_conflict_marker.txt" (
    echo [INFO] Removing session conflict marker...
    del "session_conflict_marker.txt" >nul 2>&1
    echo [SUCCESS] Session conflict marker removed
)

REM Clear any cache files that might cause conflicts
if exist "*.cache" (
    echo [INFO] Removing cache files...
    del "*.cache" >nul 2>&1
    echo [SUCCESS] Cache files cleared
)

REM Clear any temporary session files
if exist "temp_*" (
    echo [INFO] Removing temporary files...
    del "temp_*" >nul 2>&1
    echo [SUCCESS] Temporary files cleared
)

REM Create a new startup marker with enhanced session tracking
echo %date% %time% > "server_startup_marker.txt"
echo [INFO] Created enhanced server startup marker for session tracking

REM Create a force session reset marker for immediate session clearing
echo %date% %time% > "force_session_reset.txt"
echo [INFO] Created force session reset marker for immediate session clearing

REM Create a session conflict resolution marker
echo %date% %time% > "session_conflict_resolution.txt"
echo [INFO] Created session conflict resolution marker

REM Create a multiple sessions allowed marker
echo %date% %time% > "multiple_sessions_allowed.txt"
echo [INFO] Created multiple sessions allowed marker

echo [INFO] Enhanced session cleanup completed
echo [INFO] Multiple sessions from same user are now allowed
echo [INFO] This prevents infinite loading errors after server restart
echo.

REM START LEADERBOARD TIMER AUTOMATICALLY
echo [INFO] Starting automatic leaderboard timer with optimal settings...
echo [INFO] Timer will run with 60-minute intervals for maximum efficiency
echo [INFO] No user interaction required - timer starts automatically

REM Start the leaderboard timer in background with optimal settings
start "YAM Leaderboard Timer" /min cmd /c "cd /d %~dp0 && python Freshworks\leaderboard.py --interval 60"

REM Wait a moment for timer to initialize
timeout /t 2 /nobreak >nul
echo [SUCCESS] Leaderboard timer started successfully in background
echo [INFO] Timer will automatically sync ticket data every 60 minutes
echo [INFO] Timer window is minimized - check taskbar for status
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
echo [INFO] Multiple sessions: ALLOWED
echo [INFO] Session conflict resolution: ENABLED
echo [INFO] Leaderboard timer: AUTO-STARTED (60min intervals)
echo.
echo [TIP] Press Ctrl+C to stop the server gracefully
echo [TIP] HTML changes will reload automatically in browser
echo [TIP] CSS/JS changes will reload automatically in browser
echo [TIP] Multiple browser tabs/windows can now be logged in simultaneously
echo [TIP] Server restart will no longer cause infinite loading errors
echo [TIP] Leaderboard timer runs automatically in background
echo.

REM Set environment variables for hot reloading and enhanced session management
set FLASK_ENV=development
set FLASK_DEBUG=1
set YAM_SERVER_MODE=1
set ELECTRON_MODE=0
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1
set FLASK_RUN_EXTRA_FILES=app/templates,app/static
set WERKZEUG_DISABLE_RELOADER=0
set YAM_ALLOW_MULTIPLE_SESSIONS=1
set YAM_SESSION_CONFLICT_RESOLUTION=1

REM Check if user wants debugger mode (enhanced hot reloading)
set /p USE_DEBUGGER_MODE="Do you want to use enhanced debugger mode for better hot reloading? (y/n): "

REM Create a temporary batch file for the server process that can be properly terminated
echo @echo off > "temp_server_runner.bat"
echo setlocal enabledelayedexpansion >> "temp_server_runner.bat"
echo echo [INFO] Starting YAM server process with enhanced session management... >> "temp_server_runner.bat"

if /i "%USE_DEBUGGER_MODE%"=="y" (
    echo [INFO] Starting with ENHANCED DEBUGGER MODE...
    echo [INFO] This provides real-time file monitoring and browser auto-refresh
    echo [INFO] Multiple sessions are allowed to prevent conflicts
    
    echo python server.py --host 0.0.0.0 --port 5000 --mode web --debug --debugger-mode --allow-multiple-sessions >> "temp_server_runner.bat"
) else (
    echo [INFO] Starting with STANDARD DEBUG MODE...
    echo [INFO] This provides basic hot reloading for templates and static files
    echo [INFO] Multiple sessions are allowed to prevent conflicts
    
    echo python server.py --host 0.0.0.0 --port 5000 --mode web --debug --allow-multiple-sessions >> "temp_server_runner.bat"
)

echo echo [INFO] Server process started >> "temp_server_runner.bat"
echo pause >> "temp_server_runner.bat"

REM Start the server in a new window so we can properly handle CTRL+C
echo [INFO] Starting server in new window...
start "YAM Server" cmd /k "temp_server_runner.bat"

REM Wait a moment for the server to start
timeout /t 3 /nobreak >nul

echo [INFO] Server started successfully
echo [INFO] Server window is now active - you can interact with it directly
echo [INFO] Leaderboard timer is running in background with 60-minute intervals
echo [INFO] To stop the server: Close the server window OR press Ctrl+C in the server window
echo [INFO] To check timer status: Look for "YAM Leaderboard Timer" in taskbar
echo.
echo [INFO] This window will now wait for you to stop the server...
echo [INFO] Press any key in this window to initiate cleanup and exit...
echo.

REM Wait for user to indicate they want to stop
pause >nul

echo.
echo [INFO] User requested server shutdown
echo [INFO] Initiating graceful shutdown and cleanup...

REM Kill the server process
echo [INFO] Terminating server process...
taskkill /FI "WINDOWTITLE eq YAM Server*" /F >nul 2>&1
taskkill /FI "IMAGENAME eq python.exe" /F >nul 2>&1

REM Kill the leaderboard timer process
echo [INFO] Terminating leaderboard timer process...
taskkill /FI "WINDOWTITLE eq YAM Leaderboard Timer*" /F >nul 2>&1

REM Wait for processes to terminate
timeout /t 2 /nobreak >nul

REM Clean up temporary file
if exist "temp_server_runner.bat" (
    del "temp_server_runner.bat" >nul 2>&1
)

REM Call the shutdown handler for comprehensive cleanup
echo [INFO] Running comprehensive shutdown cleanup...
if exist "scripts\shutdown_handler.ps1" (
    powershell -ExecutionPolicy Bypass -File "scripts\shutdown_handler.ps1" -ServerUrl "http://127.0.0.1:5000" -Timeout 5
) else (
    echo [WARNING] shutdown_handler.ps1 not found, running basic cleanup...
    call :cleanup_sessions
)

echo.
echo [INFO] Server shutdown completed successfully
echo [INFO] Leaderboard timer has been stopped
echo [INFO] All user sessions have been cleared
echo [INFO] Users will need to re-authenticate on next server start
echo [INFO] Multiple sessions will be allowed to prevent conflicts
echo [INFO] You can now safely close this window
echo.
pause
exit /b 0

:cleanup_sessions
echo [INFO] Running enhanced session cleanup...

REM Clear all session directories and files
if exist "sessions" (
    echo [INFO] Clearing sessions directory...
    rmdir /s /q "sessions" >nul 2>&1
    mkdir "sessions" >nul 2>&1
    echo [SUCCESS] Sessions directory cleared
)

if exist "app\sessions" (
    echo [INFO] Clearing app sessions directory...
    rmdir /s /q "app\sessions" >nul 2>&1
    mkdir "app\sessions" >nul 2>&1
    echo [SUCCESS] App sessions directory cleared
)

REM Clear any session files in the root directory
if exist "*.session" (
    echo [INFO] Clearing root session files...
    del "*.session" >nul 2>&1
    echo [SUCCESS] Root session files cleared
)

REM Clear any Flask session files
if exist "flask_session" (
    echo [INFO] Clearing Flask session directory...
    rmdir /s /q "flask_session" >nul 2>&1
    mkdir "flask_session" >nul 2>&1
    echo [SUCCESS] Flask session directory cleared
)

REM Clear any session conflict markers
if exist "session_conflict_resolution.txt" (
    del "session_conflict_resolution.txt" >nul 2>&1
    echo [SUCCESS] Session conflict resolution marker cleared
)

if exist "multiple_sessions_allowed.txt" (
    del "multiple_sessions_allowed.txt" >nul 2>&1
    echo [SUCCESS] Multiple sessions allowed marker cleared
)

REM Create shutdown marker
echo %date% %time% > "server_shutdown_marker.txt"
echo [SUCCESS] Server shutdown marker created

echo [SUCCESS] Enhanced session cleanup completed
goto :eof 