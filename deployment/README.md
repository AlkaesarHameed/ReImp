# Claims Processing System - Deployment Guide

This guide provides step-by-step instructions for deploying the Claims Processing System to a fresh environment. It is designed to be used by AI agents or developers.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Starting Services](#starting-services)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.13+ | Backend API |
| Node.js | 20.0.0+ | Frontend build |
| npm | 10.0.0+ | Package management |
| Docker | 24.0+ | Container services |
| Docker Compose | 2.20+ | Service orchestration |
| Git | 2.40+ | Version control |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| Ollama | Latest | Local LLM inference |
| Tesseract OCR | 5.0+ | Fallback OCR provider |

---

## Quick Start

For a quick deployment, run these commands in order:

```bash
# 1. Clone repository
git clone <repository-url>
cd ReImp

# 2. Start infrastructure services
docker compose -f docker-compose.local.yml up -d postgres redis minio

# 3. Set up Python environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 4. Configure environment
copy deployment\.env.template .env  # Windows
# cp deployment/.env.template .env  # Linux/Mac
# Edit .env with your settings

# 5. Run database migrations
python -m alembic upgrade head

# 6. Start backend
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload

# 7. In a new terminal - Start frontend
cd frontend
npm install
npm start
```

Access the application:
- **Frontend UI**: http://localhost:4200
- **Backend API**: http://localhost:8002
- **API Documentation**: http://localhost:8002/docs

---

## Detailed Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd ReImp
```

### Step 2: Start Infrastructure Services

The system requires PostgreSQL, Redis, and MinIO. Start them using Docker Compose:

```bash
docker compose -f docker-compose.local.yml up -d postgres redis minio
```

Wait for services to be healthy:
```bash
docker compose -f docker-compose.local.yml ps
```

**Service Ports:**
- PostgreSQL: `5433` (mapped from container 5432)
- Redis: `6380` (mapped from container 6379)
- MinIO API: `9002` (mapped from container 9000)
- MinIO Console: `9003` (mapped from container 9001)

### Step 3: Optional - Start OCR Service

For local OCR processing (requires Docker build):

```bash
docker compose -f docker-compose.local.yml up -d paddleocr
```

Wait for the container to be healthy (may take 2-3 minutes on first start):
```bash
docker compose -f docker-compose.local.yml logs -f paddleocr
```

### Step 4: Optional - Start Ollama (Local LLM)

For local LLM inference without cloud API:

```bash
docker compose -f docker-compose.local.yml up -d ollama
```

Pull required models:
```bash
docker exec claims-ollama ollama pull llama3.2
docker exec claims-ollama ollama pull nomic-embed-text
```

### Step 5: Set Up Python Environment

Create and activate virtual environment:

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### Step 6: Configure Environment Variables

Copy the template and configure:

**Windows:**
```powershell
copy deployment\.env.template .env
```

**Linux/Mac:**
```bash
cp deployment/.env.template .env
```

Edit `.env` file with your settings. See [Configuration](#configuration) section for details.

### Step 7: Set Up Frontend

```bash
cd frontend
npm install
```

---

## Configuration

### Environment Variables Reference

#### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5433` |
| `POSTGRES_DB` | Database name | `claims` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6380` |
| `SECRET_KEY` | Application secret (32+ chars) | - |
| `JWT_SECRET_KEY` | JWT signing key (32+ chars) | - |

#### LLM Configuration

Choose one of these providers:

**Option A: OpenAI (Recommended for production)**
```env
CLAIMS_LLM_PRIMARY_PROVIDER=openai
CLAIMS_OPENAI_API_KEY=sk-your-api-key
CLAIMS_OPENAI_MODEL=gpt-4o
```

**Option B: Ollama (Local, free)**
```env
CLAIMS_LLM_PRIMARY_PROVIDER=ollama
CLAIMS_OLLAMA_BASE_URL=http://localhost:11434
CLAIMS_OLLAMA_MODEL=llama3.2
```

#### OCR Configuration

**Option A: PaddleOCR (via Docker)**
```env
CLAIMS_OCR_PRIMARY_PROVIDER=paddleocr
CLAIMS_PADDLEOCR_HTTP_URL=http://localhost:9091
```

**Option B: Tesseract (Local fallback)**
```env
CLAIMS_OCR_PRIMARY_PROVIDER=tesseract
CLAIMS_OCR_FALLBACK_PROVIDER=tesseract
```

---

## Database Setup

### Run Migrations

Apply all database migrations:

```bash
python -m alembic upgrade head
```

This creates all required tables:
- `users` - User accounts
- `tenants` - Multi-tenant organizations
- `tenant_settings` - Tenant configuration
- `roles` - User roles and permissions
- `documents` - Document metadata
- `claim_documents` - Claim-specific documents
- `persons` - Extracted person data
- `associated_data` - Extracted field data
- `healthcare_providers` - Provider information
- `policies` - Insurance policies
- `members` - Policy members
- `claims` - Claim records
- `fee_schedules` - Pricing data
- `llm_settings` - AI configuration per tenant
- `validation_results` - Validation outcomes
- `edi_transactions` - EDI processing logs
- `audit_logs` - System audit trail

### Verify Database

```bash
# Connect to PostgreSQL
docker exec -it claims-postgres psql -U postgres -d claims

# List tables
\dt

# Exit
\q
```

### Rollback Migrations (if needed)

```bash
# Rollback one step
python -m alembic downgrade -1

# Rollback to specific revision
python -m alembic downgrade 20251218_000

# Rollback all
python -m alembic downgrade base
```

---

## Starting Services

### Backend API

Start the FastAPI backend:

```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

For production (without reload):
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --workers 4
```

### Frontend Application

In a separate terminal:

```bash
cd frontend
npm start
```

This starts the Angular development server on port 4200.

For production build:
```bash
cd frontend
npm run build:prod
```

---

## Verification

### Health Check Endpoints

| Service | URL | Expected Response |
|---------|-----|-------------------|
| Backend Health | http://localhost:8002/health | `{"status": "healthy"}` |
| API Docs | http://localhost:8002/docs | Swagger UI |
| Frontend | http://localhost:4200 | Login page |

### Test API

```bash
# Check health
curl http://localhost:8002/health

# Get API info
curl http://localhost:8002/api/v1/
```

### Test Document Upload

```bash
# Generate test token (development only)
TOKEN=$(python -c "from src.core.security import create_access_token; print(create_access_token({'sub': 'test-user', 'tenant_id': 'test-tenant', 'role': 'admin', 'permissions': ['documents:upload']}))")

# Upload test document
curl -X POST http://localhost:8002/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/test_claim.pdf"
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port (Windows)
netstat -ano | findstr :8002

# Kill process (Windows)
taskkill /F /PID <pid>

# Find process using port (Linux/Mac)
lsof -i :8002

# Kill process (Linux/Mac)
kill -9 <pid>
```

#### Docker Containers Not Starting

```bash
# Check logs
docker compose -f docker-compose.local.yml logs postgres
docker compose -f docker-compose.local.yml logs redis

# Restart services
docker compose -f docker-compose.local.yml restart
```

#### Database Connection Error

1. Verify PostgreSQL is running:
   ```bash
   docker ps | findstr postgres
   ```

2. Check connection settings in `.env`:
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5433
   ```

3. Test connection:
   ```bash
   docker exec -it claims-postgres psql -U postgres -d claims -c "SELECT 1"
   ```

#### Migration Errors

```bash
# Check current migration state
python -m alembic current

# Show migration history
python -m alembic history

# Stamp database to specific revision (skip migrations)
python -m alembic stamp 20251218_000
```

#### OCR Not Working

1. Check PaddleOCR container:
   ```bash
   docker ps | findstr paddleocr
   ```

2. Test OCR endpoint:
   ```bash
   curl http://localhost:9091/health
   ```

3. If PaddleOCR unavailable, system falls back to Tesseract automatically.

#### LLM Errors

1. For OpenAI - verify API key is valid
2. For Ollama - check container is running:
   ```bash
   docker exec claims-ollama ollama list
   ```

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claims Processing System                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │   Angular   │────▶│   FastAPI   │────▶│ PostgreSQL  │        │
│  │  Frontend   │     │   Backend   │     │  (pgvector) │        │
│  │  :4200      │     │   :8002     │     │   :5433     │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│                             │                                     │
│                             ├─────────────┐                      │
│                             │             │                      │
│                             ▼             ▼                      │
│                      ┌───────────┐ ┌───────────┐                │
│                      │   Redis   │ │   MinIO   │                │
│                      │   :6380   │ │   :9002   │                │
│                      └───────────┘ └───────────┘                │
│                             │                                     │
│          ┌─────────────────┼─────────────────┐                  │
│          ▼                 ▼                 ▼                  │
│   ┌───────────┐     ┌───────────┐     ┌───────────┐            │
│   │ PaddleOCR │     │  OpenAI   │     │  Ollama   │            │
│   │   :9091   │     │  (cloud)  │     │  :11434   │            │
│   └───────────┘     └───────────┘     └───────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review application logs
3. Create an issue in the repository
