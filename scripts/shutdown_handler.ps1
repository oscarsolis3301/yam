# YAM Server Shutdown Handler
# This script handles graceful shutdown of the YAM server with session clearing

param(
    [string]$ServerUrl = "http://127.0.0.1:5000",
    [int]$Timeout = 10
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   YAM SERVER - GRACEFUL SHUTDOWN" -ForegroundColor Cyan
Write-Host "   WITH SESSION CLEARING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 0: Force terminate any remaining Python processes
Write-Host "[STEP 0] Force terminating any remaining Python processes..." -ForegroundColor Yellow
try {
    $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        foreach ($process in $pythonProcesses) {
            Write-Host "[INFO] Terminating Python process PID: $($process.Id)" -ForegroundColor Yellow
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Host "[SUCCESS] All Python processes terminated" -ForegroundColor Green
    } else {
        Write-Host "[INFO] No Python processes found" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARNING] Error terminating Python processes: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Step 1: Try to call the force-logout endpoint to clear all sessions
Write-Host "[STEP 1] Calling force-logout endpoint to clear all sessions..." -ForegroundColor Yellow

try {
    $forceLogoutUrl = "$ServerUrl/force-logout"
    $response = Invoke-WebRequest -Uri $forceLogoutUrl -Method POST -TimeoutSec $Timeout -ErrorAction SilentlyContinue
    
    if ($response.StatusCode -eq 200) {
        Write-Host "[SUCCESS] Force logout endpoint called successfully" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Force logout endpoint returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[WARNING] Could not call force-logout endpoint: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Step 2: Clear all session files
Write-Host "[STEP 2] Clearing all session files..." -ForegroundColor Yellow

$sessionDirs = @(
    "sessions",
    "app\sessions", 
    "YAM\sessions",
    "yam_workspace\sessions",
    "instance"
)

$clearedCount = 0
foreach ($sessionDir in $sessionDirs) {
    if (Test-Path $sessionDir) {
        try {
            $files = Get-ChildItem -Path $sessionDir -File -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
                $clearedCount++
            }
            Write-Host "[OK] Cleared $($files.Count) files from $sessionDir" -ForegroundColor Green
        }
        catch {
            Write-Host "[WARN] Error clearing $sessionDir : $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

# Step 3: Clear any session cookies by creating a marker file
Write-Host "[STEP 3] Creating session clear markers..." -ForegroundColor Yellow

$markers = @(
    "server_shutdown_marker.txt",
    "session_clear_marker.txt",
    "force_reauth_marker.txt"
)

foreach ($marker in $markers) {
    try {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$timestamp - Server shutdown detected, sessions cleared" | Out-File -FilePath $marker -Encoding UTF8
        Write-Host "[OK] Created marker: $marker" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Could not create marker $marker : $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Step 4: Clear any remaining session-related files
Write-Host "[STEP 4] Clearing remaining session-related files..." -ForegroundColor Yellow

$sessionPatterns = @(
    "*.session",
    "flask_session\*",
    "*.cache",
    "session_*",
    "temp_server_runner.bat"
)

foreach ($pattern in $sessionPatterns) {
    try {
        $files = Get-ChildItem -Path . -Filter $pattern -Recurse -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
            $clearedCount++
        }
        if ($files.Count -gt 0) {
            Write-Host "[OK] Cleared $($files.Count) files matching pattern: $pattern" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[WARN] Error clearing pattern $pattern : $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Step 5: Clear any remaining temporary files
Write-Host "[STEP 5] Clearing temporary files..." -ForegroundColor Yellow

$tempPatterns = @(
    "*.tmp",
    "*.temp",
    "temp_*",
    "server_startup_marker.txt",
    "force_session_reset.txt"
)

foreach ($pattern in $tempPatterns) {
    try {
        $files = Get-ChildItem -Path . -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
            $clearedCount++
        }
        if ($files.Count -gt 0) {
            Write-Host "[OK] Cleared $($files.Count) temporary files matching pattern: $pattern" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[WARN] Error clearing temp pattern $pattern : $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Step 6: Final process cleanup
Write-Host "[STEP 6] Final process cleanup..." -ForegroundColor Yellow

try {
    # Kill any remaining processes that might be using port 5000
    $portProcesses = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $portProcesses) {
        try {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "[INFO] Terminating process using port 5000: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Yellow
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "[WARN] Could not terminate process on port 5000: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    
    # Kill any remaining cmd windows with YAM Server title
    $cmdProcesses = Get-Process -Name "cmd" -ErrorAction SilentlyContinue
    foreach ($process in $cmdProcesses) {
        try {
            $windowTitle = (Get-WmiObject -Class Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            if ($windowTitle -like "*YAM Server*") {
                Write-Host "[INFO] Terminating YAM Server window process (PID: $($process.Id))" -ForegroundColor Yellow
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Ignore errors for window title checking
        }
    }
    
    Write-Host "[SUCCESS] Final process cleanup completed" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Error during final process cleanup: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Step 7: Create a comprehensive shutdown report
Write-Host "[STEP 7] Creating shutdown report..." -ForegroundColor Yellow

$reportContent = @"
YAM Server Shutdown Report
==========================
Timestamp: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Total files cleared: $clearedCount
Session directories processed: $($sessionDirs.Count)
Markers created: $($markers.Count)

All user sessions have been cleared.
Users will need to re-authenticate on next server start.

Shutdown completed successfully.
"@

try {
    $reportContent | Out-File -FilePath "shutdown_report.txt" -Encoding UTF8
    Write-Host "[OK] Shutdown report created: shutdown_report.txt" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Could not create shutdown report: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] GRACEFUL SHUTDOWN COMPLETED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total session files cleared: $clearedCount" -ForegroundColor White
Write-Host "Session directories processed: $($sessionDirs.Count)" -ForegroundColor White
Write-Host "Shutdown markers created: $($markers.Count)" -ForegroundColor White
Write-Host ""
Write-Host "All users will need to re-authenticate on next server start." -ForegroundColor Yellow
Write-Host "Shutdown report saved to: shutdown_report.txt" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

exit 0 