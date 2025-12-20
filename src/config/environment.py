"""
Environment Configuration Service.
Source: Design Document Section 6.3 - Configuration Management
Verified: 2025-12-18

Provides environment-aware configuration management.
"""

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = "postgresql://localhost:5432/claims"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False


class RedisConfig(BaseModel):
    """Redis configuration."""

    url: str = "redis://localhost:6379/0"
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    bcrypt_rounds: int = 12
    encryption_key: Optional[str] = None
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = True
    requests_per_minute: int = 100
    burst_size: int = 20


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    include_request_id: bool = True
    include_trace_id: bool = True


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    metrics_enabled: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = True
    tracing_sample_rate: float = 1.0
    health_check_interval: int = 30


class APIConfig(BaseModel):
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    debug: bool = False
    docs_enabled: bool = True


class CacheConfig(BaseModel):
    """Cache configuration."""

    default_ttl: int = 3600
    max_size: int = 10000
    compression_enabled: bool = True
    compression_threshold: int = 1024


class FeatureFlags(BaseModel):
    """Feature flags."""

    enable_ml_predictions: bool = True
    enable_async_processing: bool = True
    enable_audit_logging: bool = True
    enable_phi_encryption: bool = True
    enable_rate_limiting: bool = True


class AppConfig(BaseSettings):
    """Main application configuration."""

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    app_name: str = "claims-processor"
    app_version: str = "1.0.0"

    # Component configs
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    model_config = {
        "env_prefix": "APP_",
        "env_nested_delimiter": "__",
    }

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        """Validate and normalize environment."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.environment == Environment.TESTING

    @property
    def is_staging(self) -> bool:
        """Check if running in staging."""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    def get_database_url(self) -> str:
        """Get database URL with fallback to env var."""
        return os.getenv("DATABASE_URL", self.database.url)

    def get_redis_url(self) -> str:
        """Get Redis URL with fallback to env var."""
        return os.getenv("REDIS_URL", self.redis.url)


def get_environment_config(env: Environment) -> dict[str, Any]:
    """Get environment-specific configuration overrides.

    Args:
        env: Target environment

    Returns:
        Configuration overrides for the environment
    """
    configs = {
        Environment.DEVELOPMENT: {
            "api": {"reload": True, "debug": True, "workers": 1},
            "logging": {"level": "DEBUG"},
            "monitoring": {"tracing_sample_rate": 1.0},
            "features": {"enable_phi_encryption": False},
        },
        Environment.TESTING: {
            "api": {"workers": 1},
            "logging": {"level": "WARNING"},
            "database": {"echo": False},
            "monitoring": {"metrics_enabled": False, "tracing_enabled": False},
            "features": {"enable_phi_encryption": False},
        },
        Environment.STAGING: {
            "api": {"workers": 2, "docs_enabled": True},
            "logging": {"level": "INFO"},
            "monitoring": {"tracing_sample_rate": 0.5},
            "security": {"cors_origins": ["https://staging.example.com"]},
        },
        Environment.PRODUCTION: {
            "api": {"workers": 4, "docs_enabled": False, "debug": False},
            "logging": {"level": "INFO"},
            "monitoring": {"tracing_sample_rate": 0.1},
            "security": {
                "cors_origins": ["https://claims.example.com"],
                "allowed_hosts": ["claims.example.com"],
            },
            "rate_limit": {"requests_per_minute": 60},
            "features": {"enable_phi_encryption": True},
        },
    }

    return configs.get(env, {})


@lru_cache()
def get_config() -> AppConfig:
    """Get cached application configuration.

    Returns:
        Application configuration
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    environment = Environment(env)

    # Load base config
    config = AppConfig(environment=environment)

    # Apply environment-specific overrides
    overrides = get_environment_config(environment)
    for key, value in overrides.items():
        if hasattr(config, key):
            nested_config = getattr(config, key)
            if isinstance(nested_config, BaseModel) and isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if hasattr(nested_config, nested_key):
                        setattr(nested_config, nested_key, nested_value)
            else:
                setattr(config, key, value)

    return config


def load_config_from_file(path: str | Path) -> AppConfig:
    """Load configuration from YAML file.

    Args:
        path: Path to configuration file

    Returns:
        Application configuration
    """
    import yaml

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return AppConfig(**data)


def validate_production_config(config: AppConfig) -> list[str]:
    """Validate configuration for production deployment.

    Args:
        config: Configuration to validate

    Returns:
        List of validation errors
    """
    errors = []

    if not config.is_production:
        return errors

    # Check secret key
    if config.security.secret_key == "change-me-in-production":
        errors.append("SECRET_KEY must be changed for production")

    # Check encryption key
    if config.features.enable_phi_encryption and not config.security.encryption_key:
        errors.append("ENCRYPTION_KEY required when PHI encryption is enabled")

    # Check debug mode
    if config.api.debug:
        errors.append("API debug mode must be disabled in production")

    # Check docs
    if config.api.docs_enabled:
        errors.append("API docs should be disabled in production")

    # Check allowed hosts
    if "*" in config.security.allowed_hosts:
        errors.append("ALLOWED_HOSTS should not include wildcard in production")

    # Check CORS origins
    if "*" in config.security.cors_origins:
        errors.append("CORS_ORIGINS should not include wildcard in production")

    return errors


# =============================================================================
# Environment Variables Helper
# =============================================================================


def get_required_env(name: str) -> str:
    """Get required environment variable.

    Args:
        name: Variable name

    Returns:
        Variable value

    Raises:
        ValueError: If variable is not set
    """
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Required environment variable not set: {name}")
    return value


def get_optional_env(name: str, default: str | None = None) -> str | None:
    """Get optional environment variable.

    Args:
        name: Variable name
        default: Default value

    Returns:
        Variable value or default
    """
    return os.getenv(name, default)


def get_bool_env(name: str, default: bool = False) -> bool:
    """Get boolean environment variable.

    Args:
        name: Variable name
        default: Default value

    Returns:
        Boolean value
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def get_int_env(name: str, default: int = 0) -> int:
    """Get integer environment variable.

    Args:
        name: Variable name
        default: Default value

    Returns:
        Integer value
    """
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
