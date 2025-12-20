#!/bin/bash
# Python Project Starter - Docker Entrypoint Script
# Handles container initialization and command execution
# Source: Docker entrypoint best practices
# https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#entrypoint
# Verified: 2025-11-14

set -e

# Color codes for output
# RED='\033[0;31m'  # Unused but kept for future error messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Python Project Starter - Container Init${NC}"
echo -e "${GREEN}========================================${NC}"

# ==========================================================================
# Wait for Database
# ==========================================================================
echo -e "${YELLOW}Waiting for database...${NC}"

# Parse DATABASE_URL to extract host and port
# Format: postgresql+asyncpg://user:pass@host:port/dbname
DB_HOST=$(echo $DATABASE_URL | sed -E 's/.*@([^:]+):.*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed -E 's/.*:([0-9]+)\/.*/\1/')

echo "Database host: $DB_HOST"
echo "Database port: $DB_PORT"

# Wait for database to be ready
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "${POSTGRES_USER:-starter_user}" > /dev/null 2>&1; do
  echo -e "${YELLOW}Database is unavailable - sleeping${NC}"
  sleep 2
done

echo -e "${GREEN}Database is up and ready!${NC}"

# ==========================================================================
# Wait for Redis (if configured)
# ==========================================================================
if [ -n "$REDIS_URL" ]; then
  echo -e "${YELLOW}Waiting for Redis...${NC}"

  REDIS_HOST=$(echo $REDIS_URL | sed -E 's#redis://.*@?([^:]+):.*#\1#')
  REDIS_PORT=$(echo $REDIS_URL | sed -E 's#.*:([0-9]+).*#\1#')

  echo "Redis host: $REDIS_HOST"
  echo "Redis port: $REDIS_PORT"

  until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; do
    echo -e "${YELLOW}Redis is unavailable - sleeping${NC}"
    sleep 2
  done

  echo -e "${GREEN}Redis is up and ready!${NC}"
fi

# ==========================================================================
# Database Migrations
# ==========================================================================
# Note: Flyway handles migrations in separate container
# No migration commands needed here

# ==========================================================================
# Initialize MinIO Buckets (if needed)
# ==========================================================================
# Note: minio-init service handles bucket creation
# This is placeholder for additional object storage init

# ==========================================================================
# Execute Command
# ==========================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting application...${NC}"
echo -e "${GREEN}Command: $*${NC}"
echo -e "${GREEN}========================================${NC}"

# Execute the provided command
exec "$@"
