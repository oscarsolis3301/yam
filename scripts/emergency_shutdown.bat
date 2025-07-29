@echo off
setlocal enabledelayedexpansion
echo ========================================
echo    YAM SERVER - EMERGENCY SHUTDOWN
echo    FORCE TERMINATION AND CLEANUP
echo ========================================
echo.

echo [WARNING] This will forcefully terminate ALL YAM server processes
echo [WARNING] and clear all user sessions immediately.
echo.
set /p CONFIRM="Are you sure you want to proceed? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo [INFO] Emergency shutdown cancelled.
    pause
    exit /b 0
)

echo.
echo [INFO] Starting emergency shutdown procedure...
echo.

REM Step 1: Force kill all Python processes
echo [STEP 1] Force terminating all Python processes...
taskkill /IM python.exe /F >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] All Python processes terminated
) else (
    echo [INFO] No Python processes found or already terminated
)

REM Step 2: Kill any cmd windows with YAM Server title
echo [STEP 2] Terminating YAM Server windows...
taskkill /FI "WINDOWTITLE eq YAM Server*" /F >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] YAM Server windows terminated
) else (
    echo [INFO] No YAM Server windows found
)

REM Step 3: Kill any processes using port 5000
echo [STEP 3] Terminating processes using port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING 2^>nul') do (
    set PID=%%a
    if not "!PID!"=="" (
        echo [INFO] Terminating process !PID! using port 5000
        taskkill /PID !PID! /F >nul 2>&1
        if !errorlevel! equ 0 (
            echo [SUCCESS] Process !PID! terminated
        )
    )
)

REM Step 4: Clear all session files
echo [STEP 4] Clearing all session files...

REM Clear session directories
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

REM Clear session files
if exist "*.session" (
    echo [INFO] Clearing session files...
    del "*.session" >nul 2>&1
    echo [SUCCESS] Session files cleared
)

if exist "flask_session" (
    echo [INFO] Clearing Flask session directory...
    rmdir /s /q "flask_session" >nul 2>&1
    mkdir "flask_session" >nul 2>&1
    echo [SUCCESS] Flask session directory cleared
)

REM Clear temporary files
if exist "temp_server_runner.bat" (
    echo [INFO] Removing temporary server runner...
    del "temp_server_runner.bat" >nul 2>&1
    echo [SUCCESS] Temporary server runner removed
)

if exist "server_startup_marker.txt" (
    echo [INFO] Removing startup marker...
    del "server_startup_marker.txt" >nul 2>&1
    echo [SUCCESS] Startup marker removed
)

if exist "force_session_reset.txt" (
    echo [INFO] Removing session reset marker...
    del "force_session_reset.txt" >nul 2>&1
    echo [SUCCESS] Session reset marker removed
)

REM Step 5: Create emergency shutdown marker
echo [STEP 5] Creating emergency shutdown marker...
echo %date% %time% - EMERGENCY SHUTDOWN > "emergency_shutdown_marker.txt"
echo [SUCCESS] Emergency shutdown marker created

REM Step 6: Run PowerShell cleanup if available
echo [STEP 6] Running comprehensive cleanup...
if exist "scripts\shutdown_handler.ps1" (
    powershell -ExecutionPolicy Bypass -File "scripts\shutdown_handler.ps1" -ServerUrl "http://127.0.0.1:5000" -Timeout 3
    echo [SUCCESS] PowerShell cleanup completed
) else (
    echo [WARNING] shutdown_handler.ps1 not found, basic cleanup completed
)

echo.
echo ========================================
echo [SUCCESS] EMERGENCY SHUTDOWN COMPLETED
echo ========================================
echo [INFO] All YAM server processes terminated
echo [INFO] All user sessions cleared
echo [INFO] All temporary files removed
echo [INFO] Users will need to re-authenticate on next server start
echo.
echo [INFO] You can now safely restart the server
echo [INFO] Emergency shutdown marker created: emergency_shutdown_marker.txt
echo.
pause 