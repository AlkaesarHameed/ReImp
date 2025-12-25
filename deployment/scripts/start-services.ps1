# Start All Services Script for Windows
# Usage: .\start-services.ps1 [-WithOCR] [-WithOllama]

param(
    [switch]$WithOCR,
    [switch]$WithOllama
)

Write-Host "=== Claims Processing System - Service Startup ===" -ForegroundColor Cyan

# Change to project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\..\.."

# Check if .env file exists
if (!(Test-Path ".env")) {
    Write-Host "Error: .env file not found" -ForegroundColor Red
    Write-Host "Please copy deployment\.env.template to .env and configure it"
    exit 1
}

# Start core infrastructure
Write-Host ""
Write-Host "Starting core infrastructure (PostgreSQL, Redis, MinIO)..." -ForegroundColor Yellow
docker compose -f docker-compose.local.yml up -d postgres redis minio

# Wait for PostgreSQL
Write-Host "Waiting for PostgreSQL..." -ForegroundColor Yellow
for ($i = 1; $i -le 30; $i++) {
    $result = docker exec claims-postgres pg_isready -U postgres 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PostgreSQL is ready" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
}

# Wait for Redis
Write-Host "Waiting for Redis..." -ForegroundColor Yellow
for ($i = 1; $i -le 10; $i++) {
    $result = docker exec claims-redis redis-cli ping 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Redis is ready" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
}

# Optional: Start PaddleOCR
if ($WithOCR) {
    Write-Host ""
    Write-Host "Starting PaddleOCR service..." -ForegroundColor Yellow
    docker compose -f docker-compose.local.yml up -d paddleocr
    Write-Host "PaddleOCR starting (may take 2-3 minutes)..." -ForegroundColor Yellow
}

# Optional: Start Ollama
if ($WithOllama) {
    Write-Host ""
    Write-Host "Starting Ollama service..." -ForegroundColor Yellow
    docker compose -f docker-compose.local.yml up -d ollama

    # Wait for Ollama and pull models
    Write-Host "Waiting for Ollama..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    Write-Host "Pulling LLM models..." -ForegroundColor Yellow
    docker exec claims-ollama ollama pull llama3.2
    docker exec claims-ollama ollama pull nomic-embed-text
}

# Show running services
Write-Host ""
Write-Host "Running services:" -ForegroundColor Yellow
docker compose -f docker-compose.local.yml ps

Write-Host ""
Write-Host "=== Infrastructure services started ===" -ForegroundColor Green
Write-Host ""
Write-Host "To start the backend API:" -ForegroundColor Cyan
Write-Host "  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload"
Write-Host ""
Write-Host "To start the frontend:" -ForegroundColor Cyan
Write-Host "  cd frontend; npm start"
