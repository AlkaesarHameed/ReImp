"""
Application Configuration
Pydantic Settings for environment-based configuration
Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
Verified: 2025-11-14
"""

import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Evidence: Pydantic v2 Settings with automatic .env file loading
    Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support
    Verified: 2025-11-14
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )

    # ============================================================================
    # Application Settings
    # ============================================================================
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = Field(
        default="development", description="Environment: development, staging, production, testing"
    )
    DEBUG: bool = Field(default=False, description="Debug mode (NEVER enable in production)")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    TZ: str = Field(default="UTC", description="Timezone")

    # Application Secrets
    SECRET_KEY: str = Field(
        ..., min_length=32, description="Secret key for session management (min 32 chars)"
    )
    JWT_SECRET_KEY: str = Field(
        ..., min_length=32, description="Secret key for JWT tokens (min 32 chars)"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration (minutes)"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration (days)")

    # ============================================================================
    # Database Configuration
    # ============================================================================
    POSTGRES_HOST: str = Field(default="db", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="starter_db", description="Database name")
    POSTGRES_USER: str = Field(default="starter_user", description="Database user")
    POSTGRES_PASSWORD: str = Field(..., description="Database password")

    DATABASE_URL: str | None = Field(default=None, description="Full database URL")

    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Connection timeout (seconds)")

    @property
    def database_url(self) -> str:
        """Construct DATABASE_URL if not explicitly provided"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # ============================================================================
    # Redis Configuration
    # ============================================================================
    REDIS_HOST: str = Field(default="redis", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: str | None = Field(default=None, description="Redis password")
    REDIS_URL: str | None = Field(default=None, description="Full Redis URL")

    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")
    CACHE_MAX_SIZE: int = Field(default=1000, description="Max cache size")

    @property
    def redis_url(self) -> str:
        """Construct REDIS_URL if not explicitly provided"""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ============================================================================
    # MinIO Configuration
    # ============================================================================
    MINIO_ENDPOINT: str = Field(default="minio:9000", description="MinIO endpoint")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", description="MinIO access key")
    MINIO_SECRET_KEY: str = Field(..., description="MinIO secret key")
    MINIO_SECURE: bool = Field(default=False, description="Use HTTPS for MinIO")
    MINIO_REGION: str = Field(default="us-east-1", description="MinIO region")

    MINIO_BUCKET_UPLOADS: str = Field(default="uploads", description="Uploads bucket")
    MINIO_BUCKET_ASSETS: str = Field(default="assets", description="Assets bucket")
    MINIO_BUCKET_BACKUPS: str = Field(default="backups", description="Backups bucket")

    # ============================================================================
    # LLM Configuration (OpenAI-Compatible)
    # ============================================================================
    LLM_PROVIDER: str = Field(default="ollama", description="LLM provider: openai, ollama, claude")
    LLM_API_KEY: str = Field(..., description="LLM API key")
    LLM_BASE_URL: str = Field(
        default="http://host.docker.internal:11434/v1", description="LLM API base URL"
    )
    LLM_MODEL: str = Field(default="llama3.2", description="LLM model name")
    LLM_TEMPERATURE: float = Field(default=0.7, description="LLM temperature", ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=2048, description="Max tokens for completion", gt=0)
    LLM_TIMEOUT: int = Field(default=60, description="LLM request timeout (seconds)", gt=0)

    # ============================================================================
    # Embedding Configuration
    # ============================================================================
    EMBEDDING_PROVIDER: str = Field(default="ollama", description="Embedding provider")
    EMBEDDING_API_KEY: str = Field(..., description="Embedding API key")
    EMBEDDING_BASE_URL: str = Field(
        default="http://host.docker.internal:11434/v1", description="Embedding API base URL"
    )
    EMBEDDING_MODEL: str = Field(default="qwen3-embedding:8b-fp16", description="Embedding model")
    EMBEDDING_DIMENSIONS: int = Field(default=1536, description="Embedding dimensions")

    # ============================================================================
    # FastAPI Configuration
    # ============================================================================
    API_HOST: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=4, description="API workers")
    API_RELOAD: bool = Field(default=True, description="Hot reload in development")

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:8501", "http://localhost:3000"],
        description="CORS allowed origins",
    )
    CORS_CREDENTIALS: bool = Field(default=True, description="Allow credentials")
    CORS_METHODS: list[str] = Field(default=["*"], description="Allowed methods")
    CORS_HEADERS: list[str] = Field(default=["*"], description="Allowed headers")

    @staticmethod
    def _parse_list_field(value: Any) -> Any:
        """Allow JSON arrays or comma-separated strings for list settings."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    # Fall back to CSV parsing below when JSON parse fails
                    pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS", mode="before")
    @classmethod
    def parse_cors_fields(cls, v: Any) -> Any:
        """Normalize CORS list fields from env strings."""
        return cls._parse_list_field(v)

    @field_validator("UPLOAD_ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_upload_extensions(cls, v: Any) -> Any:
        """Allow CSV or JSON input for upload extension lists."""
        return cls._parse_list_field(v)

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Requests per minute")

    # File Upload
    UPLOAD_MAX_SIZE_MB: int = Field(default=100, description="Max upload size (MB)")
    UPLOAD_ALLOWED_EXTENSIONS: list[str] = Field(
        default=[".pdf", ".txt", ".csv", ".json", ".png", ".jpg", ".jpeg"],
        description="Allowed file extensions",
    )

    # ============================================================================
    # MCP Configuration
    # ============================================================================
    MCP_ENABLED: bool = Field(default=True, description="Enable MCP server")
    MCP_SERVER_NAME: str = Field(default="starter-mcp-server", description="MCP server name")
    MCP_SERVER_VERSION: str = Field(default="1.0.0", description="MCP server version")

    # ============================================================================
    # Streamlit Configuration
    # ============================================================================
    STREAMLIT_PORT: int = Field(default=8501, description="Streamlit port")
    STREAMLIT_THEME: str = Field(default="light", description="Streamlit theme")
    STREAMLIT_SERVER_HEADLESS: bool = Field(default=True, description="Headless mode")

    # ============================================================================
    # Grafana Configuration
    # ============================================================================
    GF_SECURITY_ADMIN_USER: str = Field(default="admin", description="Grafana admin user")
    GF_SECURITY_ADMIN_PASSWORD: str = Field(..., description="Grafana admin password")

    # ============================================================================
    # Celery Configuration
    # ============================================================================
    CELERY_BROKER_URL: str | None = Field(default=None, description="Celery broker URL")
    CELERY_RESULT_BACKEND: str | None = Field(default=None, description="Celery result backend")

    @property
    def celery_broker_url(self) -> str:
        """Construct Celery broker URL"""
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return f"{self.redis_url.replace('/0', '/1')}"  # Use Redis DB 1

    @property
    def celery_result_backend(self) -> str:
        """Construct Celery result backend URL"""
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        return f"{self.redis_url.replace('/0', '/2')}"  # Use Redis DB 2

    # ============================================================================
    # OAuth2 Configuration (Optional)
    # ============================================================================
    GOOGLE_CLIENT_ID: str | None = Field(default=None, description="Google OAuth2 client ID")
    GOOGLE_CLIENT_SECRET: str | None = Field(default=None, description="Google OAuth2 secret")
    GOOGLE_REDIRECT_URI: str | None = Field(default=None, description="Google redirect URI")

    GITHUB_CLIENT_ID: str | None = Field(default=None, description="GitHub OAuth2 client ID")
    GITHUB_CLIENT_SECRET: str | None = Field(default=None, description="GitHub OAuth2 secret")
    GITHUB_REDIRECT_URI: str | None = Field(default=None, description="GitHub redirect URI")

    # ============================================================================
    # Feature Flags
    # ============================================================================
    FEATURE_RATE_LIMITING: bool = Field(default=True, description="Enable rate limiting")
    FEATURE_OAUTH2: bool = Field(default=False, description="Enable OAuth2 authentication")
    FEATURE_MCP: bool = Field(default=True, description="Enable MCP server")
    FEATURE_CELERY_TASKS: bool = Field(default=True, description="Enable Celery background tasks")

    # ============================================================================
    # Monitoring (Optional)
    # ============================================================================
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN for error tracking")
    SENTRY_ENVIRONMENT: str | None = Field(default=None, description="Sentry environment")

    # ============================================================================
    # Validation
    # ============================================================================
    @field_validator("SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def validate_secret_keys(cls, v: str) -> str:
        """
        Ensure secret keys are sufficiently long for security.

        Evidence: OWASP recommends minimum 32 characters for cryptographic keys
        Source: https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html
        Verified: 2025-11-14
        """
        if len(v) < 32:
            raise ValueError("Secret keys must be at least 32 characters long")
        return v

    # ============================================================================
    # Helper Properties
    # ============================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.ENVIRONMENT.lower() == "testing"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode"""
        return self.ENVIRONMENT.lower() == "staging"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded once and reused.
    Evidence: FastAPI dependency injection pattern for settings
    Source: https://fastapi.tiangolo.com/advanced/settings/
    Verified: 2025-11-14
    """
    return Settings()


# Backward compatibility: Keep global settings instance
# For new code, prefer using get_settings() or dependency injection
settings = get_settings()
