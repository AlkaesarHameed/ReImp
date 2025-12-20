# Integration Tests

Tests that verify interactions between components and external systems.

## Guidelines

- Test real database interactions (with test database)
- Test Redis caching behavior
- Test API endpoints end-to-end
- Use `@pytest.mark.integration` decorator
- May be slower (< 10 seconds per test)

## Structure

```
integration/
├── test_api_auth.py      # Authentication API flow tests
├── test_database.py      # Database connection and query tests
├── test_cache.py         # Redis cache integration tests
└── test_storage.py       # MinIO storage tests
```

## Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_registration_flow(client: AsyncClient):
    """Test complete user registration flow"""
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
    })

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
```
