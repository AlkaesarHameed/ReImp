# Unit Tests

Fast, isolated tests for individual components.

## Guidelines

- Test single functions/classes in isolation
- Mock external dependencies (database, Redis, APIs)
- Should run in < 1 second
- Use `@pytest.mark.unit` decorator

## Structure

```
unit/
├── test_auth.py          # Authentication utility tests
├── test_config.py        # Configuration tests
├── test_models.py        # Model validation tests
└── test_schemas.py       # Pydantic schema tests
```

## Example

```python
import pytest

@pytest.mark.unit
def test_password_hashing():
    from src.utils.auth import get_password_hash, verify_password

    password = "TestPassword123!"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)
```
