# AI Agent Deployment Instructions

This document provides machine-readable instructions for AI agents to deploy the Claims Processing System.

## Deployment Steps (Sequential)

Execute these steps in order. Wait for each step to complete before proceeding.

### Step 1: Verify Prerequisites

```bash
# Check Python version (must be 3.13+)
python --version

# Check Node.js version (must be 20+)
node --version

# Check npm version (must be 10+)
npm --version

# Check Docker
docker --version
docker compose version
```

**Expected outputs:**
- Python 3.13.x or higher
- Node v20.x.x or higher
- npm 10.x.x or higher
- Docker 24.x.x or higher
- Docker Compose v2.x.x or higher

### Step 2: Clone and Navigate to Repository

```bash
git clone <repository-url>
cd ReImp
```

### Step 3: Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, MinIO
docker compose -f docker-compose.local.yml up -d postgres redis minio

# Wait for services (30 seconds)
# On Windows:
timeout /t 30 /nobreak
# On Linux/Mac:
sleep 30

# Verify services are running
docker compose -f docker-compose.local.yml ps
```

**Expected:** All three containers show "running" or "healthy" status.

### Step 4: Create Environment Configuration

```bash
# Windows:
copy deployment\.env.template .env

# Linux/Mac:
cp deployment/.env.template .env
```

### Step 5: Configure LLM Provider

Edit `.env` file and set ONE of these configurations:

**Option A: OpenAI (requires API key)**
```
CLAIMS_LLM_PRIMARY_PROVIDER=openai
CLAIMS_OPENAI_API_KEY=sk-your-actual-api-key
CLAIMS_OPENAI_MODEL=gpt-4o
```

**Option B: Ollama (local, free)**
```
CLAIMS_LLM_PRIMARY_PROVIDER=ollama
CLAIMS_OLLAMA_BASE_URL=http://localhost:11434
CLAIMS_OLLAMA_MODEL=llama3.2
```

If using Ollama, also start the container:
```bash
docker compose -f docker-compose.local.yml up -d ollama

# Wait for Ollama to start
# Windows:
timeout /t 30 /nobreak
# Linux/Mac:
sleep 30

# Pull required model
docker exec claims-ollama ollama pull llama3.2
```

### Step 6: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 7: Run Database Migrations

```bash
python -m alembic upgrade head
```

**Expected:** Output ends with "Done" or shows successful migration application.

### Step 8: Verify Database Tables

```bash
docker exec claims-postgres psql -U postgres -d claims -c "\dt"
```

**Expected:** List of tables including:
- users
- tenants
- documents
- claim_documents
- persons
- associated_data
- claims
- (and others)

### Step 9: Start Backend API

Open a new terminal:

```bash
# Activate virtual environment first
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Start backend
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

**Expected:** Output includes "Uvicorn running on http://0.0.0.0:8002"

### Step 10: Verify Backend

```bash
curl http://localhost:8002/health
```

**Expected response:** `{"status":"healthy"}` or similar JSON with status.

### Step 11: Set Up Frontend

Open another terminal:

```bash
cd frontend
npm install
```

**Expected:** "added XXX packages" with no errors.

### Step 12: Start Frontend

```bash
npm start
```

**Expected:** Output includes "Angular Live Development Server is listening on localhost:4200"

### Step 13: Verify Frontend

```bash
curl -I http://localhost:4200
```

**Expected:** HTTP/1.1 200 OK

---

## Verification Checklist

Run these commands to verify successful deployment:

```bash
# 1. Docker containers running
docker compose -f docker-compose.local.yml ps | grep -E "(postgres|redis|minio)" | grep -c "running"
# Expected: 3

# 2. Backend health
curl -s http://localhost:8002/health | grep -c "healthy"
# Expected: 1

# 3. Frontend accessible
curl -s -o /dev/null -w "%{http_code}" http://localhost:4200
# Expected: 200

# 4. Database tables exist
docker exec claims-postgres psql -U postgres -d claims -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" -t
# Expected: 15 or more
```

---

## Common Errors and Solutions

### Error: Port 8002 already in use
```bash
# Windows:
netstat -ano | findstr :8002
taskkill /F /PID <pid>

# Linux/Mac:
lsof -i :8002
kill -9 <pid>
```

### Error: PostgreSQL connection refused
```bash
# Check if container is running
docker ps | grep postgres

# If not running, start it
docker compose -f docker-compose.local.yml up -d postgres
```

### Error: Migration fails
```bash
# Check current state
python -m alembic current

# If stuck, stamp to a known state and retry
python -m alembic stamp head
python -m alembic downgrade base
python -m alembic upgrade head
```

### Error: npm install fails
```bash
# Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

---

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:4200 | User interface |
| Backend API | http://localhost:8002 | REST API |
| API Docs | http://localhost:8002/docs | Swagger documentation |
| PostgreSQL | localhost:5433 | Database |
| Redis | localhost:6380 | Cache |
| MinIO Console | http://localhost:9003 | Object storage UI |
| PaddleOCR | http://localhost:9091 | OCR service (if started) |
| Ollama | http://localhost:11434 | LLM service (if started) |

---

## Shutdown Commands

```bash
# Stop all Docker services
docker compose -f docker-compose.local.yml down

# Stop backend (Ctrl+C in terminal or)
# Windows:
taskkill /F /FI "WINDOWTITLE eq uvicorn*"

# Stop frontend (Ctrl+C in terminal)
```
