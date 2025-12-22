# Port Configuration Instructions

## Overview

This project uses a **Single Source of Truth** pattern for managing all service ports and URLs. All port configurations are defined in `config/ports.yaml` and automatically propagated to all other configuration files.

---

## Quick Start

### First-Time Setup

```bash
# 1. Install PyYAML if not already installed
pip install pyyaml

# 2. Generate all configuration files
python scripts/generate-config.py

# 3. Start all services
docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
```

### Daily Development

```bash
# Option 1: Use the startup script (recommended)
scripts\start-dev.bat          # Windows
./scripts/start-dev.sh         # Linux/Mac

# Option 2: Manual steps
python scripts/generate-config.py
docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
uvicorn src.api.main:app --port 8002 --reload
```

---

## How to Change Ports

### Step 1: Edit `config/ports.yaml`

Open `config/ports.yaml` and find the service you want to change:

```yaml
services:
  api:
    host: localhost
    port: 8002          # <-- Change this value
    internal_port: 8000
```

### Step 2: Run the Generator

```bash
python scripts/generate-config.py
```

This automatically updates:
- `.env.ports` (backend environment variables)
- `docker/docker-compose.ports.yml` (Docker port mappings)
- `frontend/apps/claims-portal/proxy.conf.json` (Angular proxy)
- `frontend/apps/claims-portal/src/environments/environment.ts` (Angular environment)

### Step 3: Restart Services

```bash
docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
```

---

## Port Reference

| Service | External Port | Internal Port | Description |
|---------|--------------|---------------|-------------|
| API | 8002 | 8000 | FastAPI backend |
| PostgreSQL | 5433 | 5432 | Database |
| Redis | 6380 | 6379 | Cache |
| MinIO API | 9000 | 9000 | Object storage |
| MinIO Console | 9001 | 9001 | MinIO UI |
| PaddleOCR | 9091 | 9090 | OCR service |
| Typesense | 8108 | 8108 | Search engine |
| Ollama | 11434 | 11434 | LLM server |
| Grafana | 3000 | 3000 | Monitoring |
| Prometheus | 9090 | 9090 | Metrics |
| PgAdmin | 5050 | 80 | DB admin |
| Redis Commander | 8081 | 8081 | Redis admin |
| Angular Dev | 4200 | - | Frontend |

---

## Configuration Files

### Source (Edit This)

| File | Purpose |
|------|---------|
| `config/ports.yaml` | **SINGLE SOURCE OF TRUTH** - All ports defined here |

### Generated (Never Edit Manually)

| File | Purpose |
|------|---------|
| `.env.ports` | Backend port environment variables |
| `docker/docker-compose.ports.yml` | Docker port mappings |
| `frontend/.../proxy.conf.json` | Angular proxy to backend |
| `frontend/.../environment.ts` | Angular environment |

### Manual Configuration (Edit as Needed)

| File | Purpose |
|------|---------|
| `.env` | Secrets (passwords, API keys) |
| `docker/docker-compose.local.yml` | Base Docker services (no ports) |

---

## Troubleshooting

### "Connection refused" or Wrong Port Errors

1. **Verify ports.yaml is correct:**
   ```bash
   cat config/ports.yaml | grep -A2 "service_name"
   ```

2. **Regenerate all configs:**
   ```bash
   python scripts/generate-config.py
   ```

3. **Restart Docker with updated config:**
   ```bash
   docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml down
   docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
   ```

4. **Check service health:**
   ```bash
   curl -s http://localhost:9000/minio/health/live   # MinIO
   curl -s http://localhost:9091/health               # PaddleOCR
   curl -s http://localhost:8108/health               # Typesense
   ```

### Port Already in Use

```bash
# Windows - Find process using port
netstat -ano | findstr :8002

# Kill process
taskkill /PID <pid> /F

# Linux/Mac - Find process using port
lsof -i :8002

# Kill process
kill -9 <pid>
```

### Configuration Not Taking Effect

1. Check you're using the correct docker-compose command:
   ```bash
   # CORRECT - includes port override file
   docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d

   # WRONG - missing port override
   docker compose -f docker/docker-compose.local.yml up -d
   ```

2. Verify generated files exist:
   ```bash
   ls -la .env.ports
   ls -la docker/docker-compose.ports.yml
   ```

---

## Why This Approach?

### The Problem (Before)

- 5+ different files contained port configurations
- Each file was edited independently
- Ports frequently got out of sync
- "Connection refused" errors were common
- Debugging took hours

### The Solution (Now)

- **ONE file** (`config/ports.yaml`) defines all ports
- **ONE command** (`python scripts/generate-config.py`) updates everything
- **ZERO manual editing** of downstream config files
- **ZERO port mismatch errors**

---

## File Locations

```
ReImp/
├── config/
│   ├── ports.yaml              # <-- EDIT THIS ONLY
│   └── INSTRUCTIONS.md         # This file
├── scripts/
│   ├── generate-config.py      # Configuration generator
│   ├── start-dev.bat           # Windows startup script
│   └── start-dev.sh            # Linux/Mac startup script
├── docker/
│   ├── docker-compose.local.yml     # Base services
│   └── docker-compose.ports.yml     # GENERATED - port mappings
├── .env                             # Secrets (passwords, keys)
├── .env.ports                       # GENERATED - port variables
└── frontend/
    └── apps/claims-portal/
        ├── proxy.conf.json          # GENERATED
        └── src/environments/
            └── environment.ts       # GENERATED
```

---

## Related Documentation

- [Design Doc 09: Centralized Configuration Management](../docs/design/09-centralized-configuration-management.md)
- [Configuration Compatibility Standards](../.claude/config-compatibility.md)
