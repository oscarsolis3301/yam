# Leaderboard Sync Timer Launcher
Write-Host "🕐 Starting Leaderboard Sync Timer..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Options:" -ForegroundColor Yellow
Write-Host "1. Quick Status Check" -ForegroundColor White
Write-Host "2. Live Timer (60 min intervals)" -ForegroundColor White
Write-Host "3. Live Timer (30 min intervals)" -ForegroundColor White
Write-Host "4. Live Timer (15 min intervals)" -ForegroundColor White
Write-Host "5. Live Timer (5 min intervals)" -ForegroundColor White
Write-Host "6. Start Leaderboard Sync (60 min intervals)" -ForegroundColor Green
Write-Host "7. Start Leaderboard Sync (30 min intervals)" -ForegroundColor Green
Write-Host ""

$choice = Read-Host "Enter your choice (1-7)"

switch ($choice) {
    "1" {
        Write-Host "Running quick status check..." -ForegroundColor Green
        python sync_timer.py --quick
        Read-Host "Press Enter to continue"
    }
    "2" {
        Write-Host "Starting live timer with 60-minute intervals..." -ForegroundColor Green
        python sync_timer.py --interval 60
    }
    "3" {
        Write-Host "Starting live timer with 30-minute intervals..." -ForegroundColor Green
        python sync_timer.py --interval 30
    }
    "4" {
        Write-Host "Starting live timer with 15-minute intervals..." -ForegroundColor Green
        python sync_timer.py --interval 15
    }
    "5" {
        Write-Host "Starting live timer with 5-minute intervals..." -ForegroundColor Green
        python sync_timer.py --interval 5
    }
    "6" {
        Write-Host "Starting leaderboard sync with 60-minute intervals..." -ForegroundColor Green
        python leaderboard.py --interval 60
    }
    "7" {
        Write-Host "Starting leaderboard sync with 30-minute intervals..." -ForegroundColor Green
        python leaderboard.py --interval 30
    }
    default {
        Write-Host "Invalid choice. Running quick status check..." -ForegroundColor Red
        python sync_timer.py --quick
        Read-Host "Press Enter to continue"
    }
} 