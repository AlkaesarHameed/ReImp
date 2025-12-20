# Deployment Guide

This guide covers deploying the Python FastAPI starter to production environments.

**⚠️ IMPORTANT**: This template has never been deployed to production. These are recommended best practices to implement before your first deployment.

---

## Table of Contents

- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Environment Configuration](#environment-configuration)
- [Security Hardening](#security-hardening)
- [Docker Production Build](#docker-production-build)
- [Cloud Deployment](#cloud-deployment)
- [Database Management](#database-management)
- [Monitoring & Logging](#monitoring--logging)
- [Backup & Disaster Recovery](#backup--disaster-recovery)
- [Scaling Strategies](#scaling-strategies)
- [Post-Deployment](#post-deployment)

---

## Pre-Deployment Checklist

Before deploying to production, ensure you've completed ALL items:

### Security

- [ ] All secrets generated with strong random values (≥32 characters)
- [ ] Secrets stored in vault/secret manager (AWS Secrets Manager, Google Secret Manager, Azure Key Vault)
- [ ] `.env` file NOT committed to git
- [ ] `DEBUG=false` in production environment
- [ ] `ENVIRONMENT=production` set correctly
- [ ] CORS configured for actual production domains only
- [ ] Rate limiting configured and tested
- [ ] HTTPS/TLS certificates configured
- [ ] Database passwords meet complexity requirements
- [ ] OAuth2 client secrets rotated and secured

### Code Quality

- [ ] All tests passing (`make test`)
- [ ] 80%+ code coverage achieved
- [ ] Security scans clean (`make security-check`)
- [ ] No linting errors (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Pre-commit hooks configured

### Infrastructure

- [ ] Database backups configured with retention policy
- [ ] Redis persistence enabled (if needed)
- [ ] MinIO/S3 backups configured
- [ ] Monitoring dashboards created
- [ ] Log aggregation configured
- [ ] Health check endpoints implemented
- [ ] Resource limits configured (CPU, memory, disk)

### Documentation

- [ ] API documentation up to date
- [ ] Deployment runbook created
- [ ] Incident response plan documented
- [ ] On-call rotation defined

---

## Environment Configuration

### Production Environment Variables

**Critical Settings** (`.env` in production):

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Security - NEVER hardcode these!
SECRET_KEY=${SECRET_FROM_VAULT}           # ≥32 chars
JWT_SECRET_KEY=${JWT_SECRET_FROM_VAULT}   # ≥32 chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15            # Short for production
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=${DATABASE_URL_FROM_VAULT}
POSTGRES_HOST=${DB_HOST}
POSTGRES_PORT=5432
POSTGRES_DB=prod_db
POSTGRES_USER=${DB_USER_FROM_VAULT}
POSTGRES_PASSWORD=${DB_PASSWORD_FROM_VAULT}

# Redis
REDIS_URL=${REDIS_URL_FROM_VAULT}
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=6379

# MinIO / S3
MINIO_ENDPOINT=${S3_ENDPOINT}
MINIO_ACCESS_KEY=${S3_ACCESS_KEY_FROM_VAULT}
MINIO_SECRET_KEY=${S3_SECRET_KEY_FROM_VAULT}
MINIO_SECURE=true                        # HTTPS only

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Feature Flags
FEATURE_RATE_LIMITING=true
FEATURE_OAUTH2=true
FEATURE_MCP=true
FEATURE_CELERY_TASKS=true
```

### Secret Management

**DO NOT use .env files in production!** Use a secret manager:

#### AWS Secrets Manager

```python
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='prod/api/secrets')
    return json.loads(response['SecretString'])

# In src/api/config.py
secrets = get_secrets()
SECRET_KEY = secrets['SECRET_KEY']
JWT_SECRET_KEY = secrets['JWT_SECRET_KEY']
```

#### Google Cloud Secret Manager

```python
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

SECRET_KEY = get_secret("SECRET_KEY")
JWT_SECRET_KEY = get_secret("JWT_SECRET_KEY")
```

#### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)

SECRET_KEY = client.get_secret("SECRET-KEY").value
JWT_SECRET_KEY = client.get_secret("JWT-SECRET-KEY").value
```

---

## Security Hardening

### Application Security

**1. HTTPS/TLS Only**

```yaml
# docker-compose.prod.yml or reverse proxy config
services:
  api:
    environment:
      - FORCE_HTTPS=true
```

Configure reverse proxy (Nginx, Traefik, or cloud load balancer) with TLS certificates:

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://api:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
    }
}
```

**2. Rate Limiting**

Implement at reverse proxy level for DoS protection:

```nginx
# nginx rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://api:8000;
}
```

**3. Security Headers**

Add security headers via middleware or reverse proxy:

```python
# src/api/main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### Database Security

**1. Connection Security**

```bash
# Use SSL for database connections
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

**2. Network Isolation**

```yaml
# docker-compose.prod.yml
networks:
  backend:
    internal: true # No external access
  frontend:
    driver: bridge

services:
  db:
    networks:
      - backend # Only accessible by API
  api:
    networks:
      - backend
      - frontend
```

**3. Principle of Least Privilege**

```sql
-- Create application user with minimal permissions
CREATE USER app_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE prod_db TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- DO NOT grant DROP, TRUNCATE, or DDL permissions to app_user
```

---

## Docker Production Build

### Multi-Stage Production Dockerfile

```dockerfile
# Production Dockerfile
FROM python:3.12-slim AS builder

# Install Poetry
RUN pip install poetry==1.8.0

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies (production only)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Production stage
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy application code
WORKDIR /app
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser database/ ./database/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Build and Tag

```bash
# Build production image
docker build -f Dockerfile.prod -t yourapp:$(git rev-parse --short HEAD) .

# Tag for registry
docker tag yourapp:$(git rev-parse --short HEAD) registry.yourdomain.com/yourapp:latest
docker tag yourapp:$(git rev-parse --short HEAD) registry.yourdomain.com/yourapp:1.0.0

# Push to registry
docker push registry.yourdomain.com/yourapp:latest
docker push registry.yourdomain.com/yourapp:1.0.0
```

---

## Cloud Deployment

### AWS (ECS + RDS + ElastiCache)

**Architecture:**

```
[Route 53] → [ALB] → [ECS Fargate] → [RDS PostgreSQL]
                              ↓
                         [ElastiCache Redis]
                              ↓
                            [S3]
```

**Terraform Example:**

```hcl
# main.tf
resource "aws_ecs_cluster" "main" {
  name = "yourapp-cluster"
}

resource "aws_ecs_task_definition" "api" {
  family                   = "yourapp-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"

  container_definitions = jsonencode([{
    name  = "api"
    image = "registry.yourdomain.com/yourapp:latest"
    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_url.arn }
    ]
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
  }])
}

resource "aws_db_instance" "postgres" {
  identifier        = "yourapp-db"
  engine            = "postgres"
  engine_version    = "17.2"
  instance_class    = "db.t3.medium"
  allocated_storage = 100

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az               = true
  publicly_accessible    = false
}
```

### Google Cloud (Cloud Run + Cloud SQL + Memorystore)

```yaml
# cloudbuild.yaml
steps:
  # Build
  - name: "gcr.io/cloud-builders/docker"
    args: ["build", "-t", "gcr.io/$PROJECT_ID/yourapp:$SHORT_SHA", "."]

  # Push
  - name: "gcr.io/cloud-builders/docker"
    args: ["push", "gcr.io/$PROJECT_ID/yourapp:$SHORT_SHA"]

  # Deploy to Cloud Run
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: gcloud
    args:
      - "run"
      - "deploy"
      - "yourapp-api"
      - "--image=gcr.io/$PROJECT_ID/yourapp:$SHORT_SHA"
      - "--region=us-central1"
      - "--platform=managed"
      - "--allow-unauthenticated"
```

### Azure (App Service + Azure Database for PostgreSQL)

```yaml
# azure-pipelines.yml
trigger:
  - main

pool:
  vmImage: "ubuntu-latest"

steps:
  - task: Docker@2
    inputs:
      containerRegistry: "yourregistry"
      repository: "yourapp"
      command: "buildAndPush"
      Dockerfile: "**/Dockerfile.prod"
      tags: |
        $(Build.BuildId)
        latest

  - task: AzureWebAppContainer@1
    inputs:
      appName: "yourapp-api"
      azureSubscription: "yoursubscription"
      imageName: "yourregistry.azurecr.io/yourapp:$(Build.BuildId)"
```

---

## Database Management

### Migrations in Production

**CRITICAL: Always backup before migrations!**

```bash
# 1. Backup database
pg_dump -h prod-db.example.com -U app_user -d prod_db -F c -b -v -f backup_$(date +%Y%m%d_%H%M%S).dump

# 2. Test migration on staging first
flyway -url=jdbc:postgresql://staging-db:5432/staging_db -user=app_user -password=$PASSWORD migrate

# 3. Apply to production (during maintenance window)
flyway -url=jdbc:postgresql://prod-db:5432/prod_db -user=app_user -password=$PASSWORD migrate

# 4. Verify
flyway -url=jdbc:postgresql://prod-db:5432/prod_db -user=app_user -password=$PASSWORD info
```

### Database Backups

**Automated Backups (AWS RDS example):**

```hcl
resource "aws_db_instance" "postgres" {
  backup_retention_period = 30          # 30 days
  backup_window          = "03:00-04:00" # UTC
  copy_tags_to_snapshot  = true

  # Point-in-time recovery
  enabled_cloudwatch_logs_exports = ["postgresql"]
}
```

**Manual Backup Script:**

```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_HOST="prod-db.example.com"
DB_NAME="prod_db"
DB_USER="app_user"

# Create backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -b -v \
    -f $BACKUP_DIR/backup_$DATE.dump

# Upload to S3
aws s3 cp $BACKUP_DIR/backup_$DATE.dump s3://yourapp-backups/postgresql/backup_$DATE.dump

# Cleanup old local backups (keep 7 days)
find $BACKUP_DIR -name "backup_*.dump" -mtime +7 -delete
```

---

## Monitoring & Logging

### Application Monitoring

**Health Check Endpoint:**

```python
# src/api/routes/health.py
from fastapi import APIRouter
from src.db.connection import check_db_connection

router = APIRouter()

@router.get("/health")
async def health_check():
    db_healthy = await check_db_connection()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "up" if db_healthy else "down",
        "version": "1.0.0"
    }
```

**Prometheus Metrics:**

```python
# src/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
active_connections = Gauge('api_active_connections', 'Active database connections')
```

### Centralized Logging

**Structured Logging (Production):**

```python
# src/utils/logging.py
import logging
import json_logging
import sys

json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

logger = logging.getLogger("yourapp")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
```

**Log Aggregation (AWS CloudWatch example):**

```python
import watchtower

cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group='/aws/ecs/yourapp',
    stream_name='api-{strftime:%Y-%m-%d}'
)
logger.addHandler(cloudwatch_handler)
```

### Grafana Dashboards

**Key Metrics to Monitor:**

- API request rate and latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database connection pool usage
- Redis hit/miss ratio
- CPU and memory usage
- Disk I/O
- Active user sessions

---

## Backup & Disaster Recovery

### Backup Strategy

**3-2-1 Rule:**

- 3 copies of data
- 2 different storage types
- 1 offsite backup

**Backup Schedule:**

- **Database**: Daily full backup, hourly incremental (if possible)
- **Object Storage (MinIO/S3)**: Versioning enabled + cross-region replication
- **Configuration**: Version controlled in git
- **Logs**: Retained for 30-90 days

### Disaster Recovery Plan

**RTO (Recovery Time Objective)**: 4 hours
**RPO (Recovery Point Objective)**: 1 hour

**Recovery Procedures:**

1. **Database Corruption:**

   ```bash
   # Restore from latest backup
   pg_restore -h new-db.example.com -U app_user -d prod_db backup_20251114_020000.dump
   ```

2. **Complete Infrastructure Failure:**

   - Deploy to backup region from IaC (Terraform/CloudFormation)
   - Restore database from latest backup
   - Update DNS to point to backup region
   - Verify application functionality

3. **Data Loss:**
   - Identify point-in-time to restore
   - Restore from backup to staging environment
   - Verify data integrity
   - Promote staging to production

---

## Scaling Strategies

### Horizontal Scaling

**API Instances:**

```yaml
# docker-compose.prod.yml or Kubernetes deployment
services:
  api:
    deploy:
      replicas: 4 # Run 4 instances
      resources:
        limits:
          cpus: "1"
          memory: 1G
```

**Load Balancing:**

- Use cloud load balancer (ALB, Google Cloud Load Balancing, Azure Load Balancer)
- Session affinity not required (stateless API with JWT)

### Database Scaling

**Read Replicas:**

```python
# src/db/connection.py
read_engine = create_async_engine(READ_REPLICA_URL)
write_engine = create_async_engine(PRIMARY_DB_URL)

# Use read replica for queries
async def get_users():
    async with AsyncSession(read_engine) as session:
        result = await session.execute(select(User))
        return result.scalars().all()
```

**Connection Pooling:**

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Base connections
    max_overflow=10,     # Burst capacity
    pool_timeout=30,
    pool_recycle=3600,   # Recycle connections every hour
)
```

### Caching Strategy

**Redis Caching:**

```python
from functools import wraps
import redis

cache = redis.from_url(REDIS_URL)

def cached(ttl=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cached_value = cache.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            result = await func(*args, **kwargs)
            cache.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

---

## Post-Deployment

### Smoke Tests

```bash
#!/bin/bash
# smoke-test.sh

API_URL="https://api.yourdomain.com"

# Health check
curl -f $API_URL/health || exit 1

# Authentication
curl -f -X POST $API_URL/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}' || exit 1

echo "Smoke tests passed!"
```

### Monitoring Checklist

- [ ] Health check endpoint returns 200
- [ ] Database connections successful
- [ ] Redis connections successful
- [ ] MinIO/S3 accessible
- [ ] Logs flowing to aggregation service
- [ ] Metrics visible in Grafana
- [ ] Alerts configured and tested
- [ ] SSL certificate valid and not expiring soon

### Rollback Plan

```bash
# Rollback to previous version
kubectl set image deployment/yourapp-api api=registry.yourdomain.com/yourapp:previous-tag

# Or with Docker Compose
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-build
```

---

## Additional Resources

- [12-Factor App Methodology](https://12factor.net/)
- [OWASP Deployment Security](https://owasp.org/www-project-proactive-controls/)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/high-availability.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

**Last Updated**: 2025-11-14

**Version**: 1.0.0
