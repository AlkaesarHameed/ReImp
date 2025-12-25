#!/bin/bash
# Start All Services Script
# Usage: ./start-services.sh [--with-ocr] [--with-ollama]

set -e

echo "=== Claims Processing System - Service Startup ==="

WITH_OCR=false
WITH_OLLAMA=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --with-ocr)
            WITH_OCR=true
            shift
            ;;
        --with-ollama)
            WITH_OLLAMA=true
            shift
            ;;
    esac
done

# Change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please copy deployment/.env.template to .env and configure it"
    exit 1
fi

# Start core infrastructure
echo ""
echo "Starting core infrastructure (PostgreSQL, Redis, MinIO)..."
docker compose -f docker-compose.local.yml up -d postgres redis minio

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker exec claims-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "PostgreSQL is ready"
        break
    fi
    sleep 1
done

# Wait for Redis
echo "Waiting for Redis..."
for i in {1..10}; do
    if docker exec claims-redis redis-cli ping > /dev/null 2>&1; then
        echo "Redis is ready"
        break
    fi
    sleep 1
done

# Optional: Start PaddleOCR
if [ "$WITH_OCR" = true ]; then
    echo ""
    echo "Starting PaddleOCR service..."
    docker compose -f docker-compose.local.yml up -d paddleocr
    echo "PaddleOCR starting (may take 2-3 minutes)..."
fi

# Optional: Start Ollama
if [ "$WITH_OLLAMA" = true ]; then
    echo ""
    echo "Starting Ollama service..."
    docker compose -f docker-compose.local.yml up -d ollama

    # Wait for Ollama and pull models
    echo "Waiting for Ollama..."
    sleep 10
    echo "Pulling LLM models..."
    docker exec claims-ollama ollama pull llama3.2 || true
    docker exec claims-ollama ollama pull nomic-embed-text || true
fi

# Show running services
echo ""
echo "Running services:"
docker compose -f docker-compose.local.yml ps

echo ""
echo "=== Infrastructure services started ==="
echo ""
echo "To start the backend API:"
echo "  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm start"
