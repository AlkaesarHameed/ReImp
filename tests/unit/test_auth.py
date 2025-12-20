"""
Unit Tests for Authentication Utilities
Tests password hashing and JWT token generation in isolation
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_password_hashing(self):
        """Test that passwords are hashed correctly"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Hash should not equal original password
        assert hashed != password
        # Hash should be a bcrypt hash (starts with $2b$)
        assert hashed.startswith("$2b$")

    def test_password_verification(self):
        """Test that password verification works"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Correct password should verify
        assert verify_password(password, hashed) is True
        # Wrong password should not verify
        assert verify_password("WrongPassword123!", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that same password hashed twice produces different hashes"""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different (bcrypt uses salt)
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and decoding"""

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Token should be a string
        assert isinstance(token, str)
        # Token should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        # Token should be a string
        assert isinstance(token, str)
        # Token should have 3 parts
        assert len(token.split(".")) == 3

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)

        # Payload should be decoded
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """Test decoding an invalid token"""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)

        # Should return None for invalid token
        assert payload is None

    def test_access_token_type(self):
        """Test that access token has correct type"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload["type"] == "access"

    def test_refresh_token_type(self):
        """Test that refresh token has correct type"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        payload = decode_token(token)

        assert payload["type"] == "refresh"

    def test_custom_expiration(self):
        """Test custom expiration time"""
        data = {"sub": "user123"}
        custom_expire = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=custom_expire)
        payload = decode_token(token)

        # Calculate expected expiration (approximately)
        expected_exp = datetime.now(UTC) + custom_expire
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=UTC)

        # Should be within 5 seconds of expected
        diff = abs((expected_exp - actual_exp).total_seconds())
        assert diff < 5
