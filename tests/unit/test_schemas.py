"""
Unit Tests for Pydantic Schemas
Tests validation logic for API schemas
"""

import pytest
from pydantic import ValidationError

from src.schemas.user import UserCreate, UserUpdate


@pytest.mark.unit
class TestUserCreateSchema:
    """Test UserCreate schema validation"""

    def test_valid_user_creation(self):
        """Test that valid user data passes validation"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "TestPassword123!",
        }
        user = UserCreate(**user_data)

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password == "TestPassword123!"

    def test_password_too_short(self):
        """Test that password < 12 characters is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Short1!",  # Only 7 characters
            )

        errors = exc_info.value.errors()
        assert any("at least 12 characters" in str(error) for error in errors)

    def test_password_no_uppercase(self):
        """Test that password without uppercase is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="testpassword123!",  # No uppercase
            )

        errors = exc_info.value.errors()
        assert any("uppercase letter" in str(error) for error in errors)

    def test_password_no_lowercase(self):
        """Test that password without lowercase is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="TESTPASSWORD123!",  # No lowercase
            )

        errors = exc_info.value.errors()
        assert any("lowercase letter" in str(error) for error in errors)

    def test_password_no_digit(self):
        """Test that password without digit is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="TestPassword!",  # No digit
            )

        errors = exc_info.value.errors()
        assert any("digit" in str(error) for error in errors)

    def test_password_no_special_character(self):
        """Test that password without special character is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="TestPassword123",  # No special character
            )

        errors = exc_info.value.errors()
        assert any("special character" in str(error) for error in errors)

    def test_invalid_email(self):
        """Test that invalid email is rejected"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                username="testuser",
                password="TestPassword123!",
            )

    def test_username_too_short(self):
        """Test that username < 3 characters is rejected"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="ab",  # Only 2 characters
                password="TestPassword123!",
            )

    def test_username_too_long(self):
        """Test that username > 100 characters is rejected"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="a" * 101,  # 101 characters
                password="TestPassword123!",
            )


@pytest.mark.unit
class TestUserUpdateSchema:
    """Test UserUpdate schema validation"""

    def test_partial_update(self):
        """Test that partial updates are allowed"""
        # All fields optional
        update = UserUpdate(email="new@example.com")
        assert update.email == "new@example.com"
        assert update.username is None

        update2 = UserUpdate(username="newusername")
        assert update2.username == "newusername"
        assert update2.email is None

    def test_empty_update(self):
        """Test that empty update is allowed"""
        update = UserUpdate()
        assert update.email is None
        assert update.username is None
        assert update.full_name is None
