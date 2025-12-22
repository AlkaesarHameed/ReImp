# Centralized Port/URL Configuration Management

## Document Information

| Field | Value |
|-------|-------|
| Document ID | 09 |
| Title | Centralized Configuration Management |
| Status | Research Complete |
| Created | 2025-12-22 |
| Author | Claude Code |
| Problem Duration | 10+ days of port configuration drift |

---

## Executive Summary

This document presents a solution for permanently eliminating port/URL configuration mismatches across the ReImp Claims Processing System. The proposed approach establishes a **Single Source of Truth** pattern where all service ports and URLs are defined in one file (`config/ports.yaml`) and automatically propagated to all downstream configurations.

---

## 1. Problem Analysis

### 1.1 Current Configuration Locations (5 Independent Sources)

| Location | File | Purpose | Current Values |
|----------|------|---------|----------------|
| Docker Compose | `docker/docker-compose.local.yml` | Container port mappings | MinIO: 9000:9000, Redis: 6380:6379, DB: 5433:5432 |
| Backend Environment | `.env` | Runtime configuration | MINIO_ENDPOINT=localhost:9002 |
| Backend Defaults | `src/api/config.py` | Fallback values | Various hardcoded defaults |
| Claims Config | `src/core/config.py` | Claims-specific settings | PADDLEOCR_HTTP_URL=localhost:9091 |
| Frontend Proxy | `frontend/.../proxy.conf.json` | API proxy routing | target: localhost:8003 |
| Frontend Environment | `frontend/.../environment.ts` | Angular runtime config | wsUrl: localhost:8005 |

### 1.2 Root Cause

The current architecture violates the **Single Source of Truth** principle:
- Each component maintains its own configuration independently
- No automated synchronization between configurations
- Manual updates are error-prone and incomplete
- Docker port mappings don't match application expectations

### 1.3 Impact

- 10+ days of debugging configuration mismatches
- Services fail to connect (e.g., MinIO HTTPConnectionPool errors)
- Developer productivity loss
- Inconsistent behavior across environments

---

## 2. Research Findings

### 2.1 Industry Best Practices

#### From Docker Documentation
> "The .env file can serve as the single source of truth for all deployment configuration, loaded automatically by Docker Compose."

Source: [Docker Docs - Environment Variables Best Practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)

#### From Microservices.io
> "Configuration includes URLs of other microservices to talk to. Each microservice will have a separate configuration for different environments. That's where a centralized configuration server steps in."

Source: [Microservices.io - Externalized Configuration](https://microservices.io/patterns/externalized-configuration.html)

#### From F5/NGINX Best Practices
> "An example is the hostname and port at which the service connects to another microservice. Such values can change at any time and need to be registered with some central configuration storage when they are changed."

Source: [F5 - Best Practices for Configuring Microservices Apps](https://www.f5.com/company/blog/nginx/best-practices-for-configuring-microservices-apps)

### 2.2 Evaluated Approaches

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **A. Code Generation from YAML** | Simple, no runtime deps, full control | Requires running generator | **RECOMMENDED** |
| B. Docker Compose Variable Interpolation | Native Docker support | Doesn't cover frontend configs | Partial solution |
| C. Config Server (Spring Cloud Config) | Dynamic updates, enterprise-ready | Overkill for this project size | Not recommended |
| D. HashiCorp Consul/Vault | Powerful, service discovery | Complex setup, operational overhead | Not recommended |
| E. Environment-only (.env everywhere) | Simple concept | Can't generate docker-compose ports | Partial solution |

---

## 3. Proposed Solution

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    config/ports.yaml                                │
│                  (SINGLE SOURCE OF TRUTH)                           │
│   - All service ports defined once                                  │
│   - All URLs derived from ports                                     │
│   - Version controlled                                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    scripts/generate-config.py                       │
│   - Reads ports.yaml                                                │
│   - Generates all downstream configurations                         │
│   - Runs automatically on startup                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  .env.generated  │    │ docker-compose   │    │ Frontend configs │
│  (backend vars)  │    │ .ports.yml       │    │ - proxy.conf.json│
│                  │    │ (port overrides) │    │ - environment.ts │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### 3.2 File Structure

```
ReImp/
├── config/
│   ├── ports.yaml              # SINGLE SOURCE - edit only this
│   └── ports.schema.json       # Optional: JSON schema for validation
├── scripts/
│   ├── generate-config.py      # Configuration generator
│   ├── start-dev.bat           # Windows startup script
│   └── start-dev.sh            # Linux/Mac startup script
├── docker/
│   ├── docker-compose.local.yml     # Base compose (no ports)
│   └── docker-compose.ports.yml     # GENERATED: port mappings
├── .env                             # User secrets (not generated)
├── .env.ports                       # GENERATED: port-related vars
├── frontend/
│   └── apps/claims-portal/
│       ├── proxy.conf.json          # GENERATED
│       └── src/environments/
│           └── environment.ts       # GENERATED
└── .gitignore                       # Ignore generated files
```

---

## 4. Implementation Details

### 4.1 Single Source: `config/ports.yaml`

```yaml
# config/ports.yaml
# ============================================================================
# SINGLE SOURCE OF TRUTH - All ports and URLs defined here
# ============================================================================
# After editing, run: python scripts/generate-config.py
# Or use: scripts/start-dev.bat (runs generator automatically)
# ============================================================================

version: "1.0"
environment: development

# =============================================================================
# Service Definitions
# =============================================================================
# Each service defines:
#   - host: hostname for connections (localhost for dev, service name for docker)
#   - port: external port (what your code connects to)
#   - internal_port: container internal port (what the service listens on)
# =============================================================================

services:
  # ---------------------------------------------------------------------------
  # Backend API
  # ---------------------------------------------------------------------------
  api:
    host: localhost
    port: 8002
    internal_port: 8000
    description: "FastAPI backend server"

  # ---------------------------------------------------------------------------
  # Database Services
  # ---------------------------------------------------------------------------
  postgres:
    host: localhost
    port: 5433
    internal_port: 5432
    database: claims
    user: postgres
    description: "PostgreSQL database"

  redis:
    host: localhost
    port: 6380
    internal_port: 6379
    db: 0
    description: "Redis cache"

  # ---------------------------------------------------------------------------
  # Object Storage
  # ---------------------------------------------------------------------------
  minio:
    host: localhost
    api_port: 9000
    console_port: 9001
    internal_api_port: 9000
    internal_console_port: 9001
    access_key: minioadmin
    description: "MinIO object storage"

  # ---------------------------------------------------------------------------
  # AI/ML Services
  # ---------------------------------------------------------------------------
  ollama:
    host: localhost
    port: 11434
    description: "Ollama LLM server"

  paddleocr:
    host: localhost
    port: 9091
    internal_port: 9090
    description: "PaddleOCR service"

  # ---------------------------------------------------------------------------
  # Search & Indexing
  # ---------------------------------------------------------------------------
  typesense:
    host: localhost
    port: 8108
    internal_port: 8108
    api_key: claims-typesense-dev-key
    description: "Typesense search engine"

  # ---------------------------------------------------------------------------
  # Monitoring & Management
  # ---------------------------------------------------------------------------
  grafana:
    host: localhost
    port: 3000
    internal_port: 3000
    description: "Grafana dashboards"

  prometheus:
    host: localhost
    port: 9090
    internal_port: 9090
    description: "Prometheus metrics"

  pgadmin:
    host: localhost
    port: 5050
    internal_port: 80
    description: "PostgreSQL admin UI"

  redis_commander:
    host: localhost
    port: 8081
    internal_port: 8081
    description: "Redis admin UI"

# =============================================================================
# Frontend Configuration
# =============================================================================
frontend:
  host: localhost
  port: 4200
  description: "Angular development server"

# =============================================================================
# URL Templates (derived from services above)
# =============================================================================
# These are computed by the generator - shown here for reference
# url_templates:
#   minio_endpoint: "${minio.host}:${minio.api_port}"
#   database_url: "postgresql://${postgres.user}@${postgres.host}:${postgres.port}/${postgres.database}"
#   redis_url: "redis://${redis.host}:${redis.port}/${redis.db}"
#   ollama_url: "http://${ollama.host}:${ollama.port}"
#   paddleocr_url: "http://${paddleocr.host}:${paddleocr.port}"
```

### 4.2 Configuration Generator: `scripts/generate-config.py`

```python
#!/usr/bin/env python3
"""
Configuration Generator - Single Source of Truth
=================================================
Generates all configuration files from config/ports.yaml

Usage:
    python scripts/generate-config.py

This script reads the central ports.yaml and generates:
    1. .env.ports - Backend environment variables for ports/URLs
    2. docker/docker-compose.ports.yml - Docker port mappings
    3. frontend/.../proxy.conf.json - Angular proxy configuration
    4. frontend/.../environment.ts - Angular environment configuration

After running this script, start services with:
    docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Project root directory
ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config" / "ports.yaml"

# Output file paths
ENV_PORTS_FILE = ROOT / ".env.ports"
DOCKER_PORTS_FILE = ROOT / "docker" / "docker-compose.ports.yml"
PROXY_CONF_FILE = ROOT / "frontend" / "apps" / "claims-portal" / "proxy.conf.json"
ENVIRONMENT_TS_FILE = ROOT / "frontend" / "apps" / "claims-portal" / "src" / "environments" / "environment.ts"


def load_config() -> dict:
    """Load the central configuration file."""
    if not CONFIG_FILE.exists():
        print(f"ERROR: Configuration file not found: {CONFIG_FILE}")
        print("Please create config/ports.yaml first.")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_header(file_type: str) -> str:
    """Generate a header comment for generated files."""
    timestamp = datetime.now().isoformat()
    return f"""# ============================================================================
# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
# ============================================================================
# Source: config/ports.yaml
# Generated: {timestamp}
# Regenerate: python scripts/generate-config.py
# ============================================================================
"""


def generate_env_ports(config: dict) -> str:
    """Generate .env.ports file with port-related environment variables."""
    services = config["services"]

    lines = [
        generate_header("env"),
        "",
        "# =============================================================================",
        "# Port Configuration (from config/ports.yaml)",
        "# =============================================================================",
        "",
        "# API",
        f"API_PORT={services['api']['port']}",
        "",
        "# Database",
        f"POSTGRES_HOST={services['postgres']['host']}",
        f"POSTGRES_PORT={services['postgres']['port']}",
        f"POSTGRES_DB={services['postgres']['database']}",
        f"POSTGRES_USER={services['postgres']['user']}",
        "",
        "# Redis",
        f"REDIS_HOST={services['redis']['host']}",
        f"REDIS_PORT={services['redis']['port']}",
        f"REDIS_DB={services['redis'].get('db', 0)}",
        "",
        "# MinIO",
        f"MINIO_ENDPOINT={services['minio']['host']}:{services['minio']['api_port']}",
        "",
        "# Ollama",
        f"LLM_BASE_URL=http://{services['ollama']['host']}:{services['ollama']['port']}/v1",
        f"CLAIMS_OLLAMA_BASE_URL=http://{services['ollama']['host']}:{services['ollama']['port']}",
        "",
        "# PaddleOCR",
        f"CLAIMS_PADDLEOCR_HTTP_URL=http://{services['paddleocr']['host']}:{services['paddleocr']['port']}",
        "",
        "# Typesense",
        f"CLAIMS_TYPESENSE_HOST={services['typesense']['host']}",
        f"CLAIMS_TYPESENSE_PORT={services['typesense']['port']}",
        "",
        "# Monitoring",
        f"GRAFANA_PORT={services['grafana']['port']}",
        f"PROMETHEUS_PORT={services['prometheus']['port']}",
        "",
    ]

    return "\n".join(lines)


def generate_docker_compose_ports(config: dict) -> str:
    """Generate docker-compose.ports.yml with port mappings."""
    services = config["services"]

    compose = {
        "services": {
            "minio": {
                "ports": [
                    f"{services['minio']['api_port']}:{services['minio']['internal_api_port']}",
                    f"{services['minio']['console_port']}:{services['minio']['internal_console_port']}"
                ]
            },
            "db": {
                "ports": [
                    f"{services['postgres']['port']}:{services['postgres']['internal_port']}"
                ]
            },
            "redis": {
                "ports": [
                    f"{services['redis']['port']}:{services['redis']['internal_port']}"
                ]
            },
            "paddleocr": {
                "ports": [
                    f"{services['paddleocr']['port']}:{services['paddleocr']['internal_port']}"
                ]
            },
            "typesense": {
                "ports": [
                    f"{services['typesense']['port']}:{services['typesense']['internal_port']}"
                ]
            },
            "grafana": {
                "ports": [
                    f"{services['grafana']['port']}:{services['grafana']['internal_port']}"
                ]
            },
            "prometheus": {
                "ports": [
                    f"{services['prometheus']['port']}:{services['prometheus']['internal_port']}"
                ]
            },
            "pgadmin": {
                "ports": [
                    f"{services['pgadmin']['port']}:{services['pgadmin']['internal_port']}"
                ]
            },
            "redis-commander": {
                "ports": [
                    f"{services['redis_commander']['port']}:{services['redis_commander']['internal_port']}"
                ]
            }
        }
    }

    header = generate_header("yaml")
    yaml_content = yaml.dump(compose, default_flow_style=False, sort_keys=False)

    return header + "\n" + yaml_content


def generate_proxy_conf(config: dict) -> str:
    """Generate Angular proxy.conf.json."""
    api = config["services"]["api"]

    proxy = {
        "/api": {
            "target": f"http://{api['host']}:{api['port']}",
            "secure": False,
            "changeOrigin": True,
            "logLevel": "debug"
        },
        "/ws": {
            "target": f"ws://{api['host']}:{api['port']}",
            "secure": False,
            "ws": True,
            "changeOrigin": True,
            "logLevel": "debug"
        }
    }

    # JSON doesn't support comments, so we add a _comment field
    proxy["_comment"] = "AUTO-GENERATED from config/ports.yaml - DO NOT EDIT"

    return json.dumps(proxy, indent=2)


def generate_environment_ts(config: dict) -> str:
    """Generate Angular environment.ts."""
    api = config["services"]["api"]
    timestamp = datetime.now().isoformat()

    return f'''/**
 * ============================================================================
 * AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * ============================================================================
 * Source: config/ports.yaml
 * Generated: {timestamp}
 * Regenerate: python scripts/generate-config.py
 * ============================================================================
 */
import {{ Environment }} from './environment.interface';

export const environment: Environment = {{
  production: false,

  // API Configuration (from config/ports.yaml)
  apiUrl: '/api/v1',
  wsUrl: 'ws://{api["host"]}:{api["port"]}/ws',

  // Session Configuration
  sessionTimeout: 15 * 60 * 1000, // 15 minutes

  // Logging
  enableAuditLogging: true,
  logLevel: 'debug',

  // Feature Flags
  features: {{
    enableWebSocket: true,
    enableOfflineMode: false,
    enableAnalytics: false,
  }},
}};
'''


def main():
    """Main entry point."""
    print("=" * 70)
    print("Configuration Generator - Single Source of Truth")
    print("=" * 70)
    print(f"Reading: {CONFIG_FILE}")
    print()

    # Load configuration
    config = load_config()

    # Generate all files
    files_generated = []

    # 1. Generate .env.ports
    print(f"Generating: {ENV_PORTS_FILE}")
    ENV_PORTS_FILE.write_text(generate_env_ports(config), encoding="utf-8")
    files_generated.append(ENV_PORTS_FILE)

    # 2. Generate docker-compose.ports.yml
    print(f"Generating: {DOCKER_PORTS_FILE}")
    DOCKER_PORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOCKER_PORTS_FILE.write_text(generate_docker_compose_ports(config), encoding="utf-8")
    files_generated.append(DOCKER_PORTS_FILE)

    # 3. Generate proxy.conf.json
    print(f"Generating: {PROXY_CONF_FILE}")
    PROXY_CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROXY_CONF_FILE.write_text(generate_proxy_conf(config), encoding="utf-8")
    files_generated.append(PROXY_CONF_FILE)

    # 4. Generate environment.ts
    print(f"Generating: {ENVIRONMENT_TS_FILE}")
    ENVIRONMENT_TS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENVIRONMENT_TS_FILE.write_text(generate_environment_ts(config), encoding="utf-8")
    files_generated.append(ENVIRONMENT_TS_FILE)

    print()
    print("=" * 70)
    print("SUCCESS: All configuration files generated!")
    print("=" * 70)
    print()
    print("Generated files:")
    for f in files_generated:
        print(f"  - {f.relative_to(ROOT)}")
    print()
    print("Next steps:")
    print("  1. Review generated files if needed")
    print("  2. Start Docker services:")
    print("     docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d")
    print("  3. Start backend:")
    print("     uvicorn src.api.main:app --port 8002 --reload")
    print("  4. Start frontend:")
    print("     cd frontend && npx nx serve claims-portal")
    print()


if __name__ == "__main__":
    main()
```

### 4.3 Startup Script: `scripts/start-dev.bat` (Windows)

```batch
@echo off
REM ============================================================================
REM Development Startup Script - Windows
REM ============================================================================
REM This script:
REM   1. Regenerates all configuration from config/ports.yaml
REM   2. Starts Docker services with correct port mappings
REM   3. Waits for services to be healthy
REM ============================================================================

echo ============================================================================
echo ReImp Claims Processing System - Development Startup
echo ============================================================================
echo.

REM Change to project root
cd /d "%~dp0.."

REM Step 1: Generate configuration
echo [1/3] Generating configuration from ports.yaml...
python scripts/generate-config.py
if errorlevel 1 (
    echo ERROR: Configuration generation failed!
    pause
    exit /b 1
)
echo.

REM Step 2: Start Docker services
echo [2/3] Starting Docker services...
docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
if errorlevel 1 (
    echo ERROR: Docker startup failed!
    pause
    exit /b 1
)
echo.

REM Step 3: Wait for services
echo [3/3] Waiting for services to be healthy...
timeout /t 10 /nobreak > nul

REM Check service health
echo.
echo Checking service health...
curl -s -o nul -w "MinIO: %%{http_code}\n" http://localhost:9000/minio/health/live
curl -s -o nul -w "PaddleOCR: %%{http_code}\n" http://localhost:9091/health
curl -s -o nul -w "Typesense: %%{http_code}\n" http://localhost:8108/health

echo.
echo ============================================================================
echo Services are running! To start the backend:
echo   uvicorn src.api.main:app --port 8002 --reload
echo.
echo To start the frontend:
echo   cd frontend ^&^& npx nx serve claims-portal
echo ============================================================================
pause
```

### 4.4 Startup Script: `scripts/start-dev.sh` (Linux/Mac)

```bash
#!/bin/bash
# ============================================================================
# Development Startup Script - Linux/Mac
# ============================================================================

set -e

echo "============================================================================"
echo "ReImp Claims Processing System - Development Startup"
echo "============================================================================"
echo

# Change to project root
cd "$(dirname "$0")/.."

# Step 1: Generate configuration
echo "[1/3] Generating configuration from ports.yaml..."
python scripts/generate-config.py
echo

# Step 2: Start Docker services
echo "[2/3] Starting Docker services..."
docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
echo

# Step 3: Wait for services
echo "[3/3] Waiting for services to be healthy..."
sleep 10

# Check service health
echo
echo "Checking service health..."
echo -n "MinIO: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live; echo
echo -n "PaddleOCR: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:9091/health; echo
echo -n "Typesense: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:8108/health; echo

echo
echo "============================================================================"
echo "Services are running! To start the backend:"
echo "  uvicorn src.api.main:app --port 8002 --reload"
echo
echo "To start the frontend:"
echo "  cd frontend && npx nx serve claims-portal"
echo "============================================================================"
```

---

## 5. Migration Guide

### 5.1 One-Time Setup

1. **Create the configuration directory:**
   ```bash
   mkdir -p config scripts
   ```

2. **Create `config/ports.yaml`** with your current port mappings

3. **Create `scripts/generate-config.py`** with the generator code

4. **Update `.gitignore`:**
   ```gitignore
   # Generated configuration files (regenerated from config/ports.yaml)
   .env.ports
   docker/docker-compose.ports.yml
   # Note: proxy.conf.json and environment.ts are also generated
   # but may need to be committed for CI/CD pipelines
   ```

5. **Run the generator:**
   ```bash
   python scripts/generate-config.py
   ```

6. **Update your `.env` file** to source the generated ports:
   ```bash
   # At the top of .env, add:
   # Source port configuration (generated from config/ports.yaml)
   # Include .env.ports values by running: python scripts/generate-config.py
   ```

### 5.2 Ongoing Workflow

**When you need to change a port:**

1. Edit `config/ports.yaml` (the ONLY file you need to touch)
2. Run `python scripts/generate-config.py`
3. Restart Docker services:
   ```bash
   docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d
   ```

---

## 6. Validation Checklist

After implementing this solution, verify:

- [ ] All services connect successfully on first startup
- [ ] No more "connection refused" or "wrong port" errors
- [ ] Frontend proxy routes to correct backend port
- [ ] WebSocket connections work
- [ ] MinIO uploads succeed
- [ ] OCR service responds
- [ ] Database connections work

---

## 7. Sources and References

1. **Docker Documentation**
   - [Environment Variables Best Practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)
   - [Variable Interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
   - [Set Environment Variables](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)

2. **Microservices Patterns**
   - [Externalized Configuration Pattern](https://microservices.io/patterns/externalized-configuration.html)
   - [DZone - Centralized Configuration](https://dzone.com/articles/microservices-architectures-centralized-configurat)

3. **Implementation Examples**
   - [PyYAML Docker Compose Generation](https://betterprogramming.pub/using-pyyaml-to-generate-a-docker-compose-file-f9393a231038)
   - [Docker Autocompose](https://github.com/Red5d/docker-autocompose)

4. **Best Practices**
   - [F5 - Best Practices for Configuring Microservices](https://www.f5.com/company/blog/nginx/best-practices-for-configuring-microservices-apps)
   - [Microsoft - Centralized Configuration](https://learn.microsoft.com/en-us/dotnet/architecture/cloud-native/centralized-configuration)

---

## 8. Appendix: Current Port Inventory

Based on analysis of the codebase as of 2025-12-22:

| Service | Current External Port | Container Internal Port | Notes |
|---------|----------------------|------------------------|-------|
| FastAPI Backend | 8002 | 8000 | Main API |
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
