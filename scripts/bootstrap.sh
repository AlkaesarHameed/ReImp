#!/bin/bash
# Python Project Starter - Bootstrap Script
# Handles complete project setup including Poetry installation and .venv creation
# Source: CLAUDE.md Rule 0.5 - Development Environment Awareness
# Evidence: Never assume tools exist - verify and install if needed
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

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Python Project Starter - Bootstrap${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}This script will set up your development environment:${NC}"
echo -e "  1. Verify Python ${REQUIRED_PYTHON_VERSION}+ is installed"
echo -e "  2. Install Poetry ${REQUIRED_POETRY_VERSION} (if needed)"
echo -e "  3. Create .venv virtual environment"
echo -e "  4. Install project dependencies"
echo -e "  5. Set up pre-commit hooks"
echo -e "  6. Create .env file from template"
echo ""

# ==========================================================================
# Helper Functions
# ==========================================================================

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ==========================================================================
# Step 1: Check Python Installation
# ==========================================================================
echo -e "${BLUE}[Step 1/6] Checking Python installation...${NC}"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo ""
    echo -e "${RED}ERROR: Python 3 is required but not found.${NC}"
    echo ""
    echo -e "${YELLOW}Please install Python ${REQUIRED_PYTHON_VERSION} or higher:${NC}"
    echo -e "  macOS:   brew install python@${REQUIRED_PYTHON_VERSION}"
    echo -e "  Ubuntu:  sudo apt install python${REQUIRED_PYTHON_VERSION} python${REQUIRED_PYTHON_VERSION}-venv"
    echo -e "  Windows: Download from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
REQUIRED_MAJOR=$(echo $REQUIRED_PYTHON_VERSION | cut -d. -f1)
REQUIRED_MINOR=$(echo $REQUIRED_PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt "$REQUIRED_MAJOR" ] || \
   ([ "$PYTHON_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PYTHON_MINOR" -lt "$REQUIRED_MINOR" ]); then
    print_warning "Python $PYTHON_VERSION found (recommended: ${REQUIRED_PYTHON_VERSION}+)"
    echo -e "${YELLOW}Continuing anyway, but you may encounter compatibility issues.${NC}"
else
    print_success "Python $PYTHON_VERSION is installed"
fi
echo ""

# ==========================================================================
# Step 2: Check/Install Poetry
# ==========================================================================
echo -e "${BLUE}[Step 2/6] Checking Poetry installation...${NC}"

POETRY_INSTALLED=false
POETRY_VERSION_OK=false

# Check if Poetry is installed (global or in PATH)
if command -v poetry &> /dev/null; then
    POETRY_INSTALLED=true
    CURRENT_POETRY_VERSION=$(poetry --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

    if [ "$CURRENT_POETRY_VERSION" == "$REQUIRED_POETRY_VERSION" ]; then
        print_success "Poetry ${CURRENT_POETRY_VERSION} is installed (correct version)"
        POETRY_VERSION_OK=true
    else
        print_warning "Poetry ${CURRENT_POETRY_VERSION} is installed (expected: ${REQUIRED_POETRY_VERSION})"
        echo -e "${YELLOW}Version mismatch detected.${NC}"
    fi
fi

# If Poetry not installed or wrong version, offer to install
if [ "$POETRY_INSTALLED" = false ] || [ "$POETRY_VERSION_OK" = false ]; then
    echo ""
    if [ "$POETRY_INSTALLED" = false ]; then
        echo -e "${YELLOW}Poetry is not installed.${NC}"
    else
        echo -e "${YELLOW}Poetry version ${CURRENT_POETRY_VERSION} does not match required ${REQUIRED_POETRY_VERSION}.${NC}"
    fi
    echo ""
    echo -e "${BLUE}Poetry is required for dependency management in this project.${NC}"
    echo -e "${BLUE}Source: https://python-poetry.org/${NC}"
    echo ""

    read -p "$(echo -e ${YELLOW}Would you like to install Poetry ${REQUIRED_POETRY_VERSION} now? [y/N]: ${NC})" -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing Poetry ${REQUIRED_POETRY_VERSION}..."

        # Install Poetry using official installer
        # Source: https://python-poetry.org/docs/#installation
        if curl -sSL https://install.python-poetry.org | python3 - --version ${REQUIRED_POETRY_VERSION}; then
            print_success "Poetry ${REQUIRED_POETRY_VERSION} installed successfully"

            # Add Poetry to PATH for current session
            export PATH="$HOME/.local/bin:$PATH"

            # Check if Poetry is now accessible
            if command -v poetry &> /dev/null; then
                print_success "Poetry is now available in PATH"
            else
                print_warning "Poetry installed but not in PATH"
                echo -e "${YELLOW}Add to your shell profile (~/.bashrc or ~/.zshrc):${NC}"
                echo -e '  export PATH="$HOME/.local/bin:$PATH"'
                echo ""
                echo -e "${YELLOW}Then restart your shell or run:${NC}"
                echo -e '  source ~/.bashrc  # or source ~/.zshrc'
                echo ""

                # Try to continue with explicit path
                if [ -f "$HOME/.local/bin/poetry" ]; then
                    print_info "Using Poetry from $HOME/.local/bin/poetry"
                    # Use function instead of alias to avoid SC2139 warning
                    poetry() { "$HOME/.local/bin/poetry" "$@"; }
                else
                    print_error "Cannot locate Poetry executable"
                    exit 1
                fi
            fi
        else
            print_error "Failed to install Poetry"
            echo ""
            echo -e "${RED}Manual installation required:${NC}"
            echo -e "  curl -sSL https://install.python-poetry.org | python3 - --version ${REQUIRED_POETRY_VERSION}"
            echo ""
            echo -e "Or see: https://python-poetry.org/docs/#installation"
            exit 1
        fi
    else
        print_error "Poetry installation declined"
        echo ""
        echo -e "${RED}Cannot continue without Poetry.${NC}"
        echo ""
        echo -e "${YELLOW}To install manually:${NC}"
        echo -e "  curl -sSL https://install.python-poetry.org | python3 - --version ${REQUIRED_POETRY_VERSION}"
        echo ""
        echo -e "${YELLOW}Or use alternative package manager:${NC}"
        echo -e "  pipx install poetry==${REQUIRED_POETRY_VERSION}"
        echo ""
        echo -e "After installing, run this script again."
        exit 1
    fi
fi
echo ""

# ==========================================================================
# Step 3: Configure Poetry
# ==========================================================================
echo -e "${BLUE}[Step 3/6] Configuring Poetry...${NC}"

# Configure Poetry to create virtualenv in project directory
# Source: https://python-poetry.org/docs/configuration/
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true
print_success "Poetry configured to create .venv in project directory"
echo ""

# ==========================================================================
# Step 4: Create Virtual Environment and Install Dependencies
# ==========================================================================
echo -e "${BLUE}[Step 4/6] Creating virtual environment and installing dependencies...${NC}"

if [ -d ".venv" ]; then
    print_info "Virtual environment (.venv) already exists"
    read -p "$(echo -e ${YELLOW}Reinstall dependencies? [y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Reinstalling dependencies..."
        poetry install --no-interaction
        print_success "Dependencies reinstalled"
    else
        print_info "Skipping dependency installation"
    fi
else
    print_info "Creating virtual environment and installing dependencies..."
    poetry install --no-interaction
    print_success "Virtual environment created at .venv/"
    print_success "Dependencies installed"
fi
echo ""

# ==========================================================================
# Step 5: Set Up Pre-commit Hooks
# ==========================================================================
echo -e "${BLUE}[Step 5/6] Setting up pre-commit hooks...${NC}"

if [ -f ".git/hooks/pre-commit" ]; then
    print_info "Pre-commit hooks already installed"
else
    print_info "Installing pre-commit hooks..."
    if poetry run pre-commit install; then
        print_success "Pre-commit hooks installed"
    else
        print_warning "Failed to install pre-commit hooks (non-critical)"
        echo -e "${YELLOW}You can install them later with: poetry run pre-commit install${NC}"
    fi
fi
echo ""

# ==========================================================================
# Step 6: Create .env File
# ==========================================================================
echo -e "${BLUE}[Step 6/6] Creating environment configuration file...${NC}"

if [ -f ".env" ]; then
    print_info ".env file already exists"
    echo -e "${YELLOW}Existing .env file preserved.${NC}"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from .env.example"
        echo ""
        echo -e "${YELLOW}IMPORTANT: Update .env with your configuration!${NC}"
        echo ""
        echo -e "${BLUE}Required secrets (generate with: openssl rand -hex 32):${NC}"
        echo -e "  - SECRET_KEY"
        echo -e "  - JWT_SECRET_KEY"
        echo -e "  - POSTGRES_PASSWORD"
        echo -e "  - MINIO_SECRET_KEY"
        echo -e "  - GF_SECURITY_ADMIN_PASSWORD"
        echo ""
        echo -e "${YELLOW}Quick setup:${NC}"
        echo -e "  ${GREEN}openssl rand -hex 32${NC}  # Copy this for SECRET_KEY"
        echo -e "  ${GREEN}openssl rand -hex 32${NC}  # Copy this for JWT_SECRET_KEY"
    else
        print_warning ".env.example not found, cannot create .env"
    fi
fi
echo ""

# ==========================================================================
# Summary and Next Steps
# ==========================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Bootstrap Complete! ✓${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Environment Summary:${NC}"
echo -e "  Python:  $(python3 --version | awk '{print $2}')"
echo -e "  Poetry:  $(poetry --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
echo -e "  .venv:   $([ -d .venv ] && echo 'Created' || echo 'Not found')"
echo -e "  .env:    $([ -f .env ] && echo 'Exists' || echo 'Not created')"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "${BLUE}1. Update .env file with your configuration:${NC}"
echo -e "   ${GREEN}nano .env${NC}  # or use your preferred editor"
echo -e "   Generate secrets: ${GREEN}openssl rand -hex 32${NC}"
echo ""
echo -e "${BLUE}2. Start development services (Docker):${NC}"
echo -e "   ${GREEN}make dev-services${NC}"
echo -e "   This starts PostgreSQL, Redis, MinIO, and Grafana"
echo ""
echo -e "${BLUE}3. Verify setup by running tests:${NC}"
echo -e "   ${GREEN}make test${NC}"
echo ""
echo -e "${BLUE}4. Run the API locally:${NC}"
echo -e "   ${GREEN}make run-api${NC}"
echo -e "   API docs: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}For detailed documentation, see:${NC}"
echo -e "  - GETTING_STARTED.md (development guide)"
echo -e "  - CLAUDE.md (development methodology)"
echo -e "  - README.md (project overview)"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
echo ""

# ==========================================================================
# Validation Reminder
# ==========================================================================
echo -e "${BLUE}TIP: Run '${GREEN}make validate-env${BLUE}' to check your environment setup${NC}"
echo ""
