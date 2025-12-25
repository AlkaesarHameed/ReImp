# Stop All Services Script for Windows
# Usage: .\stop-services.ps1

Write-Host "=== Claims Processing System - Service Shutdown ===" -ForegroundColor Cyan

# Change to project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\..\.."

# Stop all docker containers
Write-Host ""
Write-Host "Stopping Docker services..." -ForegroundColor Yellow
docker compose -f docker-compose.local.yml down

# Kill any running backend processes on port 8002
Write-Host ""
Write-Host "Checking for backend processes on port 8002..." -ForegroundColor Yellow
$processes = netstat -ano | findstr ":8002" | findstr "LISTENING"
if ($processes) {
    $pids = $processes | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Sort-Object -Unique

    foreach ($pid in $pids) {
        if ($pid -and $pid -ne "0") {
            Write-Host "Stopping process $pid on port 8002..." -ForegroundColor Yellow
            taskkill /F /PID $pid 2>$null
        }
    }
}

# Kill any running frontend processes on port 4200
Write-Host ""
Write-Host "Checking for frontend processes on port 4200..." -ForegroundColor Yellow
$processes = netstat -ano | findstr ":4200" | findstr "LISTENING"
if ($processes) {
    $pids = $processes | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Sort-Object -Unique

    foreach ($pid in $pids) {
        if ($pid -and $pid -ne "0") {
            Write-Host "Stopping process $pid on port 4200..." -ForegroundColor Yellow
            taskkill /F /PID $pid 2>$null
        }
    }
}

Write-Host ""
Write-Host "=== All services stopped ===" -ForegroundColor Green
