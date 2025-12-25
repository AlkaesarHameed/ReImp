#!/bin/bash
# Database Setup Script
# Usage: ./setup-database.sh

set -e

echo "=== Claims Processing System - Database Setup ==="

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Not running in a virtual environment"
    echo "Consider activating your virtual environment first"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please copy deployment/.env.template to .env and configure it"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker exec claims-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Error: PostgreSQL not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Check current migration state
echo ""
echo "Checking current migration state..."
python -m alembic current

# Run migrations
echo ""
echo "Applying database migrations..."
python -m alembic upgrade head

# Verify tables
echo ""
echo "Verifying database tables..."
docker exec claims-postgres psql -U postgres -d claims -c "\dt"

echo ""
echo "=== Database setup complete ==="
