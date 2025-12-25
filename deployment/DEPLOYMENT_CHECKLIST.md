# Deployment Checklist

Use this checklist to ensure all deployment steps are completed correctly.

## Pre-Deployment

- [ ] **Prerequisites verified**
  - [ ] Python 3.13+ installed
  - [ ] Node.js 20.0.0+ installed
  - [ ] npm 10.0.0+ installed
  - [ ] Docker 24.0+ installed
  - [ ] Docker Compose 2.20+ installed
  - [ ] Git installed

## Infrastructure Setup

- [ ] **Docker services started**
  - [ ] PostgreSQL container running (port 5433)
  - [ ] Redis container running (port 6380)
  - [ ] MinIO container running (ports 9002/9003)
  - [ ] All containers healthy (`docker compose ps`)

- [ ] **Optional services**
  - [ ] PaddleOCR container running (port 9091)
  - [ ] Ollama container running (port 11434)
  - [ ] Ollama models pulled (llama3.2, nomic-embed-text)

## Backend Setup

- [ ] **Python environment**
  - [ ] Virtual environment created
  - [ ] Virtual environment activated
  - [ ] Dependencies installed (`pip install -r requirements.txt`)

- [ ] **Environment configuration**
  - [ ] `.env` file created from template
  - [ ] Database credentials configured
  - [ ] Redis connection configured
  - [ ] MinIO credentials configured
  - [ ] LLM provider configured (OpenAI or Ollama)
  - [ ] Secret keys changed from defaults

- [ ] **Database setup**
  - [ ] Migrations applied (`alembic upgrade head`)
  - [ ] All tables created (verify with `\dt` in psql)
  - [ ] No migration errors

## Frontend Setup

- [ ] **Node.js environment**
  - [ ] Dependencies installed (`npm install`)
  - [ ] No npm errors or vulnerabilities

## Service Verification

- [ ] **Backend API**
  - [ ] Service started (`uvicorn`)
  - [ ] Health check passes (`curl http://localhost:8002/health`)
  - [ ] Swagger docs accessible (`http://localhost:8002/docs`)

- [ ] **Frontend**
  - [ ] Service started (`npm start`)
  - [ ] Login page loads (`http://localhost:4200`)

- [ ] **Integration test**
  - [ ] Document upload works
  - [ ] OCR processing works
  - [ ] LLM extraction works

## Security Checklist (Production)

- [ ] **Secrets**
  - [ ] SECRET_KEY changed from default
  - [ ] JWT_SECRET_KEY changed from default
  - [ ] Database password changed from default
  - [ ] MinIO credentials changed from default

- [ ] **Network**
  - [ ] CORS origins restricted to production domains
  - [ ] Debug mode disabled (`DEBUG=false`)
  - [ ] Rate limiting enabled

- [ ] **Database**
  - [ ] Backups configured
  - [ ] Connection pooling optimized

## Post-Deployment

- [ ] **Monitoring**
  - [ ] Logs accessible
  - [ ] Health endpoints monitored
  - [ ] Error alerting configured

- [ ] **Documentation**
  - [ ] Access URLs documented
  - [ ] Admin credentials secured
  - [ ] Runbook created for common operations

---

## Quick Verification Commands

```bash
# Check all Docker containers
docker compose -f docker-compose.local.yml ps

# Test PostgreSQL
docker exec -it claims-postgres psql -U postgres -d claims -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"

# Test Redis
docker exec -it claims-redis redis-cli ping

# Test Backend
curl http://localhost:8002/health

# Test Frontend
curl -I http://localhost:4200
```
