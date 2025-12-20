"""
Unit Tests for Configuration Management
Tests settings validation and property methods
"""

import pytest
from pydantic import ValidationError

from src.api.config import Settings, get_settings


@pytest.mark.unit
class TestSettingsValidation:
    """Test configuration validation"""

    def test_secret_key_minimum_length(self):
        """Test that secret keys must be at least 32 characters"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="short",  # Too short
                JWT_SECRET_KEY="a" * 32,
                POSTGRES_PASSWORD="password",
                MINIO_SECRET_KEY="secret",
                GF_SECURITY_ADMIN_PASSWORD="admin",
                LLM_API_KEY="test",
                EMBEDDING_API_KEY="test",
            )

        # Should have validation error for SECRET_KEY
        errors = exc_info.value.errors()
        assert any("SECRET_KEY" in str(error) for error in errors)

    def test_jwt_secret_key_minimum_length(self):
        """Test that JWT secret key must be at least 32 characters"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="a" * 32,
                JWT_SECRET_KEY="short",  # Too short
                POSTGRES_PASSWORD="password",
                MINIO_SECRET_KEY="secret",
                GF_SECURITY_ADMIN_PASSWORD="admin",
                LLM_API_KEY="test",
                EMBEDDING_API_KEY="test",
            )

        errors = exc_info.value.errors()
        assert any("JWT_SECRET_KEY" in str(error) for error in errors)

    def test_environment_literal_validation(self):
        """Test that ENVIRONMENT only accepts valid values"""
        # Valid values should work
        for env in ["development", "staging", "production"]:
            settings = Settings(
                ENVIRONMENT=env,
                SECRET_KEY="a" * 32,
                JWT_SECRET_KEY="b" * 32,
                POSTGRES_PASSWORD="password",
                MINIO_SECRET_KEY="secret",
                GF_SECURITY_ADMIN_PASSWORD="admin",
                LLM_API_KEY="test",
                EMBEDDING_API_KEY="test",
            )
            assert env == settings.ENVIRONMENT

        # Invalid value should raise error
        with pytest.raises(ValidationError):
            Settings(
                ENVIRONMENT="invalid_env",
                SECRET_KEY="a" * 32,
                JWT_SECRET_KEY="b" * 32,
                POSTGRES_PASSWORD="password",
                MINIO_SECRET_KEY="secret",
                GF_SECURITY_ADMIN_PASSWORD="admin",
                LLM_API_KEY="test",
                EMBEDDING_API_KEY="test",
            )


@pytest.mark.unit
class TestSettingsProperties:
    """Test settings helper properties"""

    def test_is_development(self):
        """Test is_development property"""
        settings = Settings(
            ENVIRONMENT="development",
            SECRET_KEY="a" * 32,
            JWT_SECRET_KEY="b" * 32,
            POSTGRES_PASSWORD="password",
            MINIO_SECRET_KEY="secret",
            GF_SECURITY_ADMIN_PASSWORD="admin",
            LLM_API_KEY="test",
            EMBEDDING_API_KEY="test",
        )
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False
        assert settings.is_staging is False

    def test_is_production(self):
        """Test is_production property"""
        settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            JWT_SECRET_KEY="b" * 32,
            POSTGRES_PASSWORD="password",
            MINIO_SECRET_KEY="secret",
            GF_SECURITY_ADMIN_PASSWORD="admin",
            LLM_API_KEY="test",
            EMBEDDING_API_KEY="test",
        )
        assert settings.is_production is True
        assert settings.is_development is False
        assert settings.is_testing is False
        assert settings.is_staging is False

    def test_database_url_construction(self):
        """Test that database URL is constructed correctly"""
        settings = Settings(
            SECRET_KEY="a" * 32,
            JWT_SECRET_KEY="b" * 32,
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_DB="test_db",
            POSTGRES_USER="test_user",
            POSTGRES_PASSWORD="test_pass",
            DATABASE_URL=None,  # Explicitly disable env var to test construction
            MINIO_SECRET_KEY="secret",
            GF_SECURITY_ADMIN_PASSWORD="admin",
            LLM_API_KEY="test",
            EMBEDDING_API_KEY="test",
        )

        # Test URL components individually to avoid Pydantic masking issues
        actual_url = settings.database_url
        expected = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"

        # Compare as plain strings, ensuring type compatibility
        assert isinstance(actual_url, str), f"database_url should be str, got {type(actual_url)}"
        assert actual_url == expected, f"Expected: {expected!r}, Got: {actual_url!r}"

    def test_redis_url_construction(self):
        """Test that Redis URL is constructed correctly"""
        settings = Settings(
            SECRET_KEY="a" * 32,
            JWT_SECRET_KEY="b" * 32,
            POSTGRES_PASSWORD="password",
            REDIS_HOST="localhost",
            REDIS_PORT=6379,
            REDIS_DB=0,
            REDIS_URL=None,  # Explicitly disable env var to test construction
            MINIO_SECRET_KEY="secret",
            GF_SECURITY_ADMIN_PASSWORD="admin",
            LLM_API_KEY="test",
            EMBEDDING_API_KEY="test",
        )

        expected = "redis://localhost:6379/0"
        assert settings.redis_url == expected


@pytest.mark.unit
def test_get_settings_caching():
    """Test that get_settings() returns cached instance"""
    settings1 = get_settings()
    settings2 = get_settings()

    # Should return same instance (cached)
    assert settings1 is settings2
