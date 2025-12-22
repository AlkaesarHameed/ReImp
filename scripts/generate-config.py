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

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is not installed.")
    print("Install it with: pip install pyyaml")
    sys.exit(1)

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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        "_comment": "AUTO-GENERATED from config/ports.yaml - DO NOT EDIT MANUALLY",
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

    return json.dumps(proxy, indent=2)


def generate_environment_ts(config: dict) -> str:
    """Generate Angular environment.ts."""
    api = config["services"]["api"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    print(f"Generating: {ENV_PORTS_FILE.relative_to(ROOT)}")
    ENV_PORTS_FILE.write_text(generate_env_ports(config), encoding="utf-8")
    files_generated.append(ENV_PORTS_FILE)

    # 2. Generate docker-compose.ports.yml
    print(f"Generating: {DOCKER_PORTS_FILE.relative_to(ROOT)}")
    DOCKER_PORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOCKER_PORTS_FILE.write_text(generate_docker_compose_ports(config), encoding="utf-8")
    files_generated.append(DOCKER_PORTS_FILE)

    # 3. Generate proxy.conf.json
    print(f"Generating: {PROXY_CONF_FILE.relative_to(ROOT)}")
    PROXY_CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROXY_CONF_FILE.write_text(generate_proxy_conf(config), encoding="utf-8")
    files_generated.append(PROXY_CONF_FILE)

    # 4. Generate environment.ts
    print(f"Generating: {ENVIRONMENT_TS_FILE.relative_to(ROOT)}")
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
    print("  1. Start Docker services:")
    print("     docker compose -f docker/docker-compose.local.yml -f docker/docker-compose.ports.yml up -d")
    print()
    print("  2. Start backend:")
    print("     uvicorn src.api.main:app --port 8002 --reload")
    print()
    print("  3. Start frontend:")
    print("     cd frontend && npx nx serve claims-portal")
    print()


if __name__ == "__main__":
    main()
