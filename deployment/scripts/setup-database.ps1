# Database Setup Script for Windows
# Usage: .\setup-database.ps1

Write-Host "=== Claims Processing System - Database Setup ===" -ForegroundColor Cyan

# Check if .env file exists
if (!(Test-Path ".env")) {
    Write-Host "Error: .env file not found" -ForegroundColor Red
    Write-Host "Please copy deployment\.env.template to .env and configure it"
    exit 1
}

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL..." -ForegroundColor Yellow
$maxAttempts = 30
for ($i = 1; $i -le $maxAttempts; $i++) {
    $result = docker exec claims-postgres pg_isready -U postgres 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PostgreSQL is ready" -ForegroundColor Green
        break
    }
    if ($i -eq $maxAttempts) {
        Write-Host "Error: PostgreSQL not ready after $maxAttempts seconds" -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Seconds 1
}

# Check current migration state
Write-Host ""
Write-Host "Checking current migration state..." -ForegroundColor Yellow
python -m alembic current

# Run migrations
Write-Host ""
Write-Host "Applying database migrations..." -ForegroundColor Yellow
python -m alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Migration failed" -ForegroundColor Red
    exit 1
}

# Verify tables
Write-Host ""
Write-Host "Verifying database tables..." -ForegroundColor Yellow
docker exec claims-postgres psql -U postgres -d claims -c "\dt"

Write-Host ""
Write-Host "=== Database setup complete ===" -ForegroundColor Green
