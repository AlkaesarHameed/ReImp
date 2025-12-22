@echo off
REM ============================================================================
REM Development Startup Script - Windows
REM ============================================================================
REM This script:
REM   1. Regenerates all configuration from config/ports.yaml
REM   2. Starts Docker services with correct port mappings
REM   3. Waits for services to be healthy
REM ============================================================================

echo ============================================================================
echo ReImp Claims Processing System - Development Startup
echo ============================================================================
echo.

REM Change to project root
cd /d "%~dp0.."

REM Step 1: Generate configuration
echo [1/3] Generating configuration from ports.yaml...
python scripts/generate-config.py
if errorlevel 1 (
    echo ERROR: Configuration generation failed!
    echo Make sure PyYAML is installed: pip install pyyaml
    pause
    exit /b 1
)
echo.

REM Step 2: Start Docker services
echo [2/3] Starting Docker services...
docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
if errorlevel 1 (
    echo ERROR: Docker startup failed!
    pause
    exit /b 1
)
echo.

REM Step 3: Wait for services
echo [3/3] Waiting for services to be healthy...
timeout /t 10 /nobreak > nul

REM Check service health
echo.
echo Checking service health...
echo.

echo Checking MinIO...
curl -s -o nul -w "  MinIO (9000): HTTP %%{http_code}\n" http://localhost:9000/minio/health/live 2>nul || echo   MinIO: Not responding

echo Checking PaddleOCR...
curl -s -o nul -w "  PaddleOCR (9091): HTTP %%{http_code}\n" http://localhost:9091/health 2>nul || echo   PaddleOCR: Not responding

echo Checking Typesense...
curl -s -o nul -w "  Typesense (8108): HTTP %%{http_code}\n" http://localhost:8108/health 2>nul || echo   Typesense: Not responding

echo.
echo ============================================================================
echo Services are running!
echo ============================================================================
echo.
echo To start the backend:
echo   uvicorn src.api.main:app --port 8002 --reload
echo.
echo To start the frontend:
echo   cd frontend ^&^& npx nx serve claims-portal
echo ============================================================================
echo.
pause
