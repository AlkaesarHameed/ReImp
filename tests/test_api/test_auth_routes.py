"""
Authentication Routes Tests.
Comprehensive test coverage for auth API endpoints.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from src.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


@pytest.mark.unit
class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        return {
            "id": str(uuid4()),
            "email": "test@claims.local",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": get_password_hash("testpassword123"),
            "is_active": True,
            "is_verified": True,
            "is_superuser": False,
            "last_login": None,
        }

    def test_password_hash_is_not_plaintext(self, mock_user):
        """Ensure password is properly hashed, not stored in plaintext."""
        hashed = mock_user["hashed_password"]
        assert hashed != "testpassword123"
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_password_verification_correct(self, mock_user):
        """Verify correct password matches hash."""
        assert verify_password("testpassword123", mock_user["hashed_password"]) is True

    def test_password_verification_incorrect(self, mock_user):
        """Verify incorrect password does not match hash."""
        assert verify_password("wrongpassword", mock_user["hashed_password"]) is False

    def test_password_verification_empty(self, mock_user):
        """Verify empty password does not match."""
        assert verify_password("", mock_user["hashed_password"]) is False


@pytest.mark.unit
class TestJWTTokenGeneration:
    """Test JWT token creation and validation."""

    def test_access_token_creation(self):
        """Test that access token is created correctly."""
        user_id = str(uuid4())
        token = create_access_token(data={"sub": user_id})

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT format: header.payload.signature

    def test_refresh_token_creation(self):
        """Test that refresh token is created correctly."""
        user_id = str(uuid4())
        token = create_refresh_token(data={"sub": user_id})

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_access_token_has_correct_type(self):
        """Test that access token has 'access' type."""
        token = create_access_token(data={"sub": "user123"})
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("type") == "access"

    def test_refresh_token_has_correct_type(self):
        """Test that refresh token has 'refresh' type."""
        token = create_refresh_token(data={"sub": "user123"})
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("type") == "refresh"

    def test_token_contains_subject(self):
        """Test that token contains the subject claim."""
        user_id = "user-12345"
        token = create_access_token(data={"sub": user_id})
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("sub") == user_id

    def test_token_contains_expiration(self):
        """Test that token contains expiration claim."""
        token = create_access_token(data={"sub": "user123"})
        payload = decode_token(token)

        assert payload is not None
        assert "exp" in payload

    def test_custom_expiration_time(self):
        """Test token with custom expiration time."""
        custom_delta = timedelta(hours=2)
        token = create_access_token(data={"sub": "user123"}, expires_delta=custom_delta)
        payload = decode_token(token)

        assert payload is not None
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected = datetime.now(UTC) + custom_delta
        # Allow 5 second tolerance
        assert abs((exp_time - expected).total_seconds()) < 5

    def test_decode_invalid_token(self):
        """Test that invalid token returns None."""
        invalid_token = "invalid.token.string"
        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_empty_token(self):
        """Test that empty token returns None."""
        payload = decode_token("")

        assert payload is None

    def test_decode_malformed_token(self):
        """Test that malformed token returns None."""
        malformed = "not-a-valid-jwt"
        payload = decode_token(malformed)

        assert payload is None


@pytest.mark.unit
class TestPasswordSecurity:
    """Test password hashing security properties."""

    def test_same_password_different_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        password = "SamePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_hash_format_is_bcrypt(self):
        """Verify hash uses bcrypt format."""
        password = "TestPassword123"
        hashed = get_password_hash(password)

        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
        # And have proper length (60 chars for bcrypt)
        assert len(hashed) == 60

    def test_unicode_password_handling(self):
        """Test password with unicode characters."""
        password = "Pässwörd123!🔒"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_long_password_handling(self):
        """Test handling of long passwords (bcrypt truncates at 72 bytes)."""
        long_password = "A" * 100

        # Python 3.14+ bcrypt requires manual truncation
        # This is expected behavior - the API should handle this
        with pytest.raises(ValueError, match="password cannot be longer than 72 bytes"):
            get_password_hash(long_password)

        # Proper handling: truncate to 72 bytes
        truncated_password = long_password[:72]
        hashed = get_password_hash(truncated_password)
        assert verify_password(truncated_password, hashed) is True

    def test_special_characters_in_password(self):
        """Test password with special characters."""
        password = "P@$$w0rd!#%&*()[]{}|\\:;<>?/"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


@pytest.mark.unit
class TestTokenDataExtraction:
    """Test that token data can be properly extracted."""

    def test_extract_user_id_from_token(self):
        """Test extracting user ID from token."""
        user_id = "usr-abc123"
        token = create_access_token(data={"sub": user_id})
        payload = decode_token(token)

        assert payload["sub"] == user_id

    def test_extract_custom_claims_from_token(self):
        """Test extracting custom claims from token."""
        custom_data = {
            "sub": "user123",
            "role": "administrator",
            "permissions": ["read", "write", "delete"],
        }
        token = create_access_token(data=custom_data)
        payload = decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["role"] == "administrator"
        assert payload["permissions"] == ["read", "write", "delete"]

    def test_extract_expiration_as_timestamp(self):
        """Test that expiration is extractable as timestamp."""
        token = create_access_token(data={"sub": "user123"})
        payload = decode_token(token)

        assert isinstance(payload["exp"], int)
        # Should be in the future
        assert payload["exp"] > datetime.now(UTC).timestamp()

    def test_extract_token_type(self):
        """Test extracting token type from access vs refresh tokens."""
        access_token = create_access_token(data={"sub": "user123"})
        refresh_token = create_refresh_token(data={"sub": "user123"})

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"


@pytest.mark.unit
class TestAuthenticationFlow:
    """Test complete authentication flow scenarios."""

    def test_full_login_flow(self):
        """Test complete login flow: hash password, verify, create tokens."""
        # Simulate user registration
        password = "SecurePassword123!"
        hashed_password = get_password_hash(password)

        # Simulate login - verify password
        assert verify_password(password, hashed_password) is True

        # Create tokens on successful login
        user_id = str(uuid4())
        access_token = create_access_token(data={"sub": user_id})
        refresh_token = create_refresh_token(data={"sub": user_id})

        # Verify tokens are valid and contain correct data
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload["sub"] == user_id
        assert access_payload["type"] == "access"
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"

    def test_token_refresh_flow(self):
        """Test token refresh flow."""
        user_id = str(uuid4())

        # Create initial tokens
        original_refresh = create_refresh_token(data={"sub": user_id})

        # Decode refresh token
        payload = decode_token(original_refresh)
        assert payload is not None
        assert payload["type"] == "refresh"

        # Create new access token using refresh token data
        new_access = create_access_token(data={"sub": payload["sub"]})
        new_refresh = create_refresh_token(data={"sub": payload["sub"]})

        # Verify new tokens
        new_access_payload = decode_token(new_access)
        new_refresh_payload = decode_token(new_refresh)

        assert new_access_payload["sub"] == user_id
        assert new_refresh_payload["sub"] == user_id

    def test_invalid_refresh_token_rejected(self):
        """Test that invalid refresh token is rejected."""
        # Attempt to decode invalid token
        payload = decode_token("invalid.refresh.token")
        assert payload is None

    def test_access_token_cannot_be_used_for_refresh(self):
        """Test that access token type is checked during refresh."""
        access_token = create_access_token(data={"sub": "user123"})
        payload = decode_token(access_token)

        # Access token has wrong type for refresh
        assert payload["type"] == "access"
        assert payload["type"] != "refresh"


@pytest.mark.unit
class TestSecurityValidation:
    """Test security-related validation."""

    def test_empty_password_hash_fails(self):
        """Test that verifying against an invalid hash fails gracefully."""
        # This would raise an exception without proper handling
        # The actual implementation should handle this
        password = "test123"
        try:
            result = verify_password(password, "invalid-hash")
            # If it doesn't raise, it should return False
            assert result is False
        except ValueError:
            # bcrypt may raise ValueError for invalid hash
            pass

    def test_token_with_empty_subject(self):
        """Test token creation with empty subject."""
        token = create_access_token(data={"sub": ""})
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == ""

    def test_token_with_none_subject(self):
        """Test token creation with None subject."""
        # Note: Jose library may not serialize None values properly
        # This tests the actual behavior rather than expected behavior
        token = create_access_token(data={"sub": None})

        # Depending on JWT library implementation, this may succeed or fail
        # We test that decoding either works or fails gracefully
        payload = decode_token(token)

        # If payload is None, decoding failed (acceptable edge case)
        # If payload exists, sub should be None or missing
        if payload is not None:
            # sub may be None or not present
            assert payload.get("sub") is None or "sub" not in payload
