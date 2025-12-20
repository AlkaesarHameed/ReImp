#!/bin/bash
# Python Project Starter - Environment Validation Script
# Validates environment consistency across local, Docker, and CI/CD
# Source: CLAUDE.md Rule 0.5 - Development Environment Awareness
# Verified: 2025-11-14

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Required versions
REQUIRED_POETRY_VERSION="2.2.1"
REQUIRED_PYTHON_VERSION="3.12"

# Counters
ERRORS=0
WARNINGS=0
CHECKS=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Environment Validation Script${NC}"
echo -e "${BLUE}Python Project Starter${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Helper functions
check_pass() {
    CHECKS=$((CHECKS + 1))
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    CHECKS=$((CHECKS + 1))
    ERRORS=$((ERRORS + 1))
    echo -e "${RED}✗${NC} $1"
    echo -e "  ${RED}Error: $2${NC}"
}

check_warn() {
    CHECKS=$((CHECKS + 1))
    WARNINGS=$((WARNINGS + 1))
    echo -e "${YELLOW}⚠${NC} $1"
    echo -e "  ${YELLOW}Warning: $2${NC}"
}

# ==========================================================================
# Check 1: Python Version
# ==========================================================================
echo -e "${BLUE}[1/10] Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1,2)
    if [ "$PYTHON_VERSION" == "$REQUIRED_PYTHON_VERSION" ]; then
        check_pass "Python $PYTHON_VERSION is installed"
    else
        check_warn "Python version mismatch" "Found $PYTHON_VERSION, expected $REQUIRED_PYTHON_VERSION"
    fi
else
    check_fail "Python not found" "Install Python $REQUIRED_PYTHON_VERSION or higher"
fi
echo ""

# ==========================================================================
# Check 2: Poetry Installation
# ==========================================================================
echo -e "${BLUE}[2/10] Checking Poetry installation...${NC}"
if command -v poetry &> /dev/null; then
    check_pass "Poetry is installed"
else
    # Check in .venv if activated
    if [ -f ".venv/bin/poetry" ]; then
        check_pass "Poetry found in .venv"
    else
        check_fail "Poetry not found" "Install with: curl -sSL https://install.python-poetry.org | python3 -"
    fi
fi
echo ""

# ==========================================================================
# Check 3: Poetry Version Consistency
# ==========================================================================
echo -e "${BLUE}[3/10] Checking Poetry version consistency...${NC}"

# Check local Poetry version
if command -v poetry &> /dev/null; then
    LOCAL_POETRY=$(poetry --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [ "$LOCAL_POETRY" == "$REQUIRED_POETRY_VERSION" ]; then
        check_pass "Local Poetry version: $LOCAL_POETRY"
    else
        check_fail "Local Poetry version mismatch" "Found $LOCAL_POETRY, expected $REQUIRED_POETRY_VERSION. Run: curl -sSL https://install.python-poetry.org | python3 - --version $REQUIRED_POETRY_VERSION"
    fi
else
    check_fail "Cannot verify Poetry version" "Poetry not in PATH"
fi

# Check CI/CD workflow files
if [ -f ".github/workflows/test.yml" ]; then
    CI_POETRY=$(grep "POETRY_VERSION:" .github/workflows/test.yml | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    if [ "$CI_POETRY" == "$REQUIRED_POETRY_VERSION" ]; then
        check_pass "CI/CD Poetry version (test.yml): $CI_POETRY"
    else
        check_fail "CI/CD Poetry version mismatch (test.yml)" "Found $CI_POETRY, expected $REQUIRED_POETRY_VERSION"
    fi
fi

if [ -f ".github/workflows/lint.yml" ]; then
    LINT_POETRY=$(grep "POETRY_VERSION:" .github/workflows/lint.yml | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    if [ "$LINT_POETRY" == "$REQUIRED_POETRY_VERSION" ]; then
        check_pass "CI/CD Poetry version (lint.yml): $LINT_POETRY"
    else
        check_fail "CI/CD Poetry version mismatch (lint.yml)" "Found $LINT_POETRY, expected $REQUIRED_POETRY_VERSION"
    fi
fi

# Check pre-commit config
if [ -f ".pre-commit-config.yaml" ]; then
    PRECOMMIT_POETRY=$(grep -A1 "python-poetry/poetry" .pre-commit-config.yaml | grep "rev:" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    if [ "$PRECOMMIT_POETRY" == "$REQUIRED_POETRY_VERSION" ]; then
        check_pass "Pre-commit Poetry version: $PRECOMMIT_POETRY"
    else
        check_fail "Pre-commit Poetry version mismatch" "Found $PRECOMMIT_POETRY, expected $REQUIRED_POETRY_VERSION"
    fi
fi

# Check Dockerfiles
for dockerfile in docker/Dockerfile.api docker/Dockerfile.streamlit; do
    if [ -f "$dockerfile" ]; then
        DOCKER_POETRY=$(grep "poetry==" "$dockerfile" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        if [ "$DOCKER_POETRY" == "$REQUIRED_POETRY_VERSION" ]; then
            check_pass "Docker Poetry version ($dockerfile): $DOCKER_POETRY"
        else
            check_fail "Docker Poetry version mismatch ($dockerfile)" "Found $DOCKER_POETRY, expected $REQUIRED_POETRY_VERSION"
        fi
    fi
done
echo ""

# ==========================================================================
# Check 4: Virtual Environment
# ==========================================================================
echo -e "${BLUE}[4/10] Checking Python virtual environment (.venv)...${NC}"
if [ -d ".venv" ]; then
    check_pass "Virtual environment exists at .venv/"

    # Check if .venv has Python
    if [ -f ".venv/bin/python" ] || [ -f ".venv/Scripts/python.exe" ]; then
        check_pass "Python interpreter found in .venv"
    else
        check_fail ".venv exists but no Python interpreter" "Run: poetry install"
    fi
else
    check_fail "Virtual environment not found" "Run: poetry install"
fi
echo ""

# ==========================================================================
# Check 5: Docker Installation
# ==========================================================================
echo -e "${BLUE}[5/10] Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    check_pass "Docker is installed"

    # Check if Docker daemon is running
    if docker ps &> /dev/null; then
        check_pass "Docker daemon is running"
    else
        check_fail "Docker daemon not running" "Start Docker Desktop"
    fi
else
    check_fail "Docker not found" "Install Docker Desktop"
fi
echo ""

# ==========================================================================
# Check 6: Docker Compose
# ==========================================================================
echo -e "${BLUE}[6/10] Checking Docker Compose...${NC}"
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    check_pass "Docker Compose is available"
else
    check_fail "Docker Compose not found" "Install Docker Desktop (includes Compose)"
fi
echo ""

# ==========================================================================
# Check 7: Environment File (.env)
# ==========================================================================
echo -e "${BLUE}[7/10] Checking environment configuration (.env)...${NC}"
if [ -f ".env" ]; then
    check_pass ".env file exists"

    # Check for critical environment variables
    if grep -q "SECRET_KEY=" .env && ! grep -q "SECRET_KEY=CHANGE_ME" .env; then
        check_pass "SECRET_KEY is configured"
    else
        check_fail "SECRET_KEY not set" "Generate with: openssl rand -hex 32"
    fi

    if grep -q "JWT_SECRET_KEY=" .env && ! grep -q "JWT_SECRET_KEY=CHANGE_ME" .env; then
        check_pass "JWT_SECRET_KEY is configured"
    else
        check_fail "JWT_SECRET_KEY not set" "Generate with: openssl rand -hex 32"
    fi

    # Check DATABASE_URL uses localhost (for local development)
    if grep -q "DATABASE_URL=.*localhost" .env; then
        check_pass "DATABASE_URL uses localhost (correct for local .venv)"
    elif grep -q "DATABASE_URL=.*@db:" .env; then
        check_warn "DATABASE_URL uses 'db' hostname" "Should use 'localhost' for local development. Docker will override automatically."
    else
        check_warn "DATABASE_URL not found or malformed" "Check .env.example for correct format"
    fi
else
    check_fail ".env file not found" "Copy from .env.example: cp .env.example .env"
fi
echo ""

# ==========================================================================
# Check 8: Dependencies Installed
# ==========================================================================
echo -e "${BLUE}[8/10] Checking Python dependencies...${NC}"
if [ -f "poetry.lock" ]; then
    check_pass "poetry.lock exists"

    # Check if dependencies are installed in .venv
    if [ -d ".venv" ]; then
        # Check for a common dependency (FastAPI)
        if [ -f ".venv/bin/activate" ]; then
            # Source .venv and check for FastAPI
            if .venv/bin/python -c "import fastapi" 2>/dev/null; then
                check_pass "Dependencies installed in .venv"
            else
                check_warn "Dependencies may not be fully installed" "Run: poetry install"
            fi
        fi
    fi
else
    check_warn "poetry.lock not found" "Run: poetry install to generate"
fi
echo ""

# ==========================================================================
# Check 9: Docker Services (if running)
# ==========================================================================
echo -e "${BLUE}[9/10] Checking Docker services status...${NC}"
if docker ps &> /dev/null; then
    # Check for expected containers
    if docker ps --format '{{.Names}}' | grep -q "starter_db"; then
        check_pass "PostgreSQL container is running"
    else
        check_warn "PostgreSQL container not running" "Run: make dev-services"
    fi

    if docker ps --format '{{.Names}}' | grep -q "starter_redis"; then
        check_pass "Redis container is running"
    else
        check_warn "Redis container not running" "Run: make dev-services"
    fi

    if docker ps --format '{{.Names}}' | grep -q "starter_minio"; then
        check_pass "MinIO container is running"
    else
        check_warn "MinIO container not running" "Run: make dev-services"
    fi
else
    check_warn "Cannot check Docker services" "Docker daemon not running"
fi
echo ""

# ==========================================================================
# Check 10: Git Configuration
# ==========================================================================
echo -e "${BLUE}[10/10] Checking Git configuration...${NC}"
if git rev-parse --git-dir > /dev/null 2>&1; then
    check_pass "Git repository initialized"

    # Check if pre-commit hooks are installed
    if [ -f ".git/hooks/pre-commit" ]; then
        check_pass "Pre-commit hooks installed"
    else
        check_warn "Pre-commit hooks not installed" "Run: poetry run pre-commit install"
    fi
else
    check_warn "Not a Git repository" "Initialize with: git init"
fi
echo ""

# ==========================================================================
# Summary
# ==========================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total checks: ${CHECKS}"
echo -e "${GREEN}Passed: $((CHECKS - ERRORS - WARNINGS))${NC}"
echo -e "${YELLOW}Warnings: ${WARNINGS}${NC}"
echo -e "${RED}Errors: ${ERRORS}${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Environment validation passed!${NC}"
    echo -e "${GREEN}You're ready to develop.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Environment validation passed with warnings.${NC}"
    echo -e "${YELLOW}Review warnings above and fix if necessary.${NC}"
    exit 0
else
    echo -e "${RED}✗ Environment validation failed.${NC}"
    echo -e "${RED}Fix errors above before proceeding.${NC}"
    echo ""
    echo -e "${BLUE}Quick fixes:${NC}"
    echo -e "  1. Update Poetry: curl -sSL https://install.python-poetry.org | python3 - --version $REQUIRED_POETRY_VERSION"
    echo -e "  2. Install dependencies: poetry install"
    echo -e "  3. Create .env: cp .env.example .env"
    echo -e "  4. Start services: make dev-services"
    echo ""
    echo -e "See GETTING_STARTED.md for detailed setup instructions."
    exit 1
fi
