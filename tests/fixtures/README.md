# Test Fixtures

Shared test data and pytest fixtures for all tests.

## Purpose

- Reusable test data (users, posts, etc.)
- Pytest fixtures for common setups
- Mock data generators
- Factory functions for test objects

## Structure

```
fixtures/
├── __init__.py           # Shared fixtures
├── database.py           # Database fixtures (test session, etc.)
├── users.py              # User-related fixtures
└── sample_data.json      # Sample JSON data for testing
```

## Example

```python
# fixtures/users.py
import pytest
from src.models.user import User
from src.utils.auth import get_password_hash

@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "TestPassword123!",
    }

@pytest.fixture
async def test_user(session):
    """Create a test user in the database"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```
