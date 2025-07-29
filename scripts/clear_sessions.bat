@echo off
echo ========================================
echo    YAM SESSION CLEARANCE TOOL
echo ========================================
echo.

echo [INFO] This tool will clear all YAM sessions and force a fresh login
echo [INFO] Use this if you're experiencing redirect loops or session issues
echo.

set /p CONFIRM="Are you sure you want to clear all sessions? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo [INFO] Session clearance cancelled
    pause
    exit /b 0
)

echo.
echo [INFO] Clearing all session files and directories...

REM Clear session directories
if exist "sessions" (
    echo [INFO] Removing sessions directory...
    rmdir /s /q "sessions" >nul 2>&1
    mkdir "sessions" >nul 2>&1
    echo [SUCCESS] Sessions directory cleared
)

if exist "app\sessions" (
    echo [INFO] Removing app sessions directory...
    rmdir /s /q "app\sessions" >nul 2>&1
    mkdir "app\sessions" >nul 2>&1
    echo [SUCCESS] App sessions directory cleared
)

REM Clear session files
if exist "*.session" (
    echo [INFO] Removing session files from root...
    del "*.session" >nul 2>&1
    echo [SUCCESS] Root session files cleared
)

if exist "instance\*.session" (
    echo [INFO] Removing instance session files...
    del "instance\*.session" >nul 2>&1
    echo [SUCCESS] Instance session files cleared
)

REM Clear Flask session directory
if exist "flask_session" (
    echo [INFO] Removing Flask session directory...
    rmdir /s /q "flask_session" >nul 2>&1
    mkdir "flask_session" >nul 2>&1
    echo [SUCCESS] Flask session directory cleared
)

REM Create force session reset marker
echo %date% %time% > "force_session_reset.txt"
echo [INFO] Created force session reset marker

echo.
echo [SUCCESS] All sessions have been cleared!
echo [INFO] You will need to log in again when you restart the server
echo [INFO] Close this window and restart your YAM server
echo.
pause 