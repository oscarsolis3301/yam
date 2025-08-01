@echo off
echo 🕐 Starting Leaderboard Sync Timer...
echo.
echo Options:
echo 1. Quick Status Check
echo 2. Live Timer (60 min intervals)
echo 3. Live Timer (30 min intervals)
echo 4. Live Timer (15 min intervals)
echo 5. Live Timer (5 min intervals)
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo Running quick status check...
    python sync_timer.py --quick
    pause
) else if "%choice%"=="2" (
    echo Starting live timer with 60-minute intervals...
    python sync_timer.py --interval 60
) else if "%choice%"=="3" (
    echo Starting live timer with 30-minute intervals...
    python sync_timer.py --interval 30
) else if "%choice%"=="4" (
    echo Starting live timer with 15-minute intervals...
    python sync_timer.py --interval 15
) else if "%choice%"=="5" (
    echo Starting live timer with 5-minute intervals...
    python sync_timer.py --interval 5
) else (
    echo Invalid choice. Running quick status check...
    python sync_timer.py --quick
    pause
) 