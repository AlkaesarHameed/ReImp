# ADR-005: Test Organization Structure

**Status**: Accepted

**Date**: 2025-11-14

**Deciders**: Project Lead

---

## Context

A well-organized test suite is critical for:

- **Fast Feedback**: Developers need quick unit tests during development
- **Comprehensive Coverage**: Integration and end-to-end tests for confidence
- **Security Validation**: Adversarial testing for authentication, authorization, input validation
- **Clear Intent**: Test organization should communicate what is being tested
- **Selective Execution**: Ability to run subsets (unit only, skip slow tests, etc.)

Python projects often lack clear test organization, mixing fast unit tests with slow integration tests, making the entire suite slow and discouraging frequent test runs.

## Decision

We will organize tests into **four distinct categories** with separate directories:

1. **`tests/unit/`** - Fast, isolated tests (no external dependencies)
2. **`tests/integration/`** - Tests with external dependencies (database, Redis, APIs)
3. **`tests/fixtures/`** - Shared test data and pytest fixtures
4. **`tests/redteam/`** - Security and adversarial testing

Each test category is marked with pytest markers for selective execution.

**Key reasons:**

1. **Fast Feedback Loop**: Unit tests run in < 1 second, providing instant feedback
2. **Clear Separation**: Developers know immediately what type of test they're writing
3. **Selective Execution**: Run only unit tests during development, all tests in CI/CD
4. **Security Focus**: Dedicated redteam tests ensure security is tested systematically
5. **Shared Fixtures**: Centralized test data reduces duplication
6. **Scalability**: Structure supports growth from 10 to 10,000 tests

## Consequences

### Positive

**Developer Experience:**

- **Fast Tests**: Unit tests complete in milliseconds, encouraging TDD
- **Clear Intent**: Directory structure immediately communicates test type
- **Easy Navigation**: Developers can quickly find relevant tests
- **Parallel Execution**: Categories can run in parallel in CI/CD

**Code Quality:**

- **80% Coverage Enforced**: `--cov-fail-under=80` in pytest config
- **Security Testing**: Dedicated redteam tests catch vulnerabilities early
- **Regression Prevention**: Comprehensive test suite prevents regressions

**CI/CD Optimization:**

- **Tiered Testing**: Run unit tests on every commit, integration on PR, redteam nightly
- **Faster Pipelines**: Skip slow tests when appropriate
- **Clear Failures**: Test category in failure message aids debugging

### Negative

- **Learning Curve**: Developers must understand categories and when to use each
- **Fixture Complexity**: Shared fixtures require careful design to avoid coupling
- **More Directories**: More structure to navigate (though better than flat structure)

### Neutral

- **Migration Effort**: Existing tests need reorganization into categories
- **Marker Discipline**: Developers must remember to mark tests correctly

## Alternatives Considered

### Alternative 1: Flat Test Directory

**Description**: All tests in `tests/` directory without categorization

**Pros**:

- Simple structure
- Easy to find all tests
- No markers needed

**Cons**:

- **Slow Feedback**: Can't separate fast/slow tests
- **Unclear Intent**: Hard to know if test is unit or integration
- **No Selective Execution**: Must run all tests every time
- **Scales Poorly**: 1000+ tests in one directory is unwieldy

**Why rejected**: Doesn't scale, poor developer experience

### Alternative 2: Mirror Source Structure

**Description**: Tests mirror source code directory structure (e.g., `tests/api/routes/test_auth.py`)

**Pros**:

- Easy to find test for specific module
- Familiar pattern from some projects

**Cons**:

- **No Speed Separation**: Still mixes unit and integration tests
- **Confusing**: Same file might have both unit and integration tests
- **Hard to Run Subsets**: Can't easily run "all unit tests"

**Why rejected**: Doesn't solve fast/slow test separation problem

### Alternative 3: By Feature

**Description**: Tests organized by feature (auth, users, metrics, etc.)

**Pros**:

- Aligned with product features
- Useful for feature teams

**Cons**:

- **No Type Distinction**: Still need to separate unit/integration within feature
- **Cross-Cutting Concerns**: Where do shared/infrastructure tests go?
- **Refactoring Pain**: Feature reorganization requires test reorganization

**Why rejected**: Complements but doesn't replace type-based organization

## Implementation Notes

**Current Implementation:**

**Directory Structure:**

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── __init__.py
│   ├── README.md
│   ├── test_auth.py        # Password hashing, JWT creation
│   ├── test_config.py      # Configuration validation
│   └── test_schemas.py     # Pydantic validation
│
├── integration/             # Tests with external dependencies
│   ├── __init__.py
│   ├── README.md
│   ├── test_database.py    # Actual database connections
│   ├── test_redis.py       # Redis operations
│   └── test_api.py         # API endpoint tests
│
├── fixtures/                # Shared test data
│   ├── __init__.py
│   ├── README.md
│   ├── database.py         # Database fixtures
│   ├── auth.py             # Auth fixtures
│   └── sample_data.py      # Sample test data
│
├── redteam/                 # Security testing
│   ├── __init__.py
│   ├── README.md
│   ├── test_auth_security.py      # Password strength, SQL injection
│   ├── test_input_validation.py   # XSS, injection attacks
│   └── test_authorization.py      # Access control bypasses
│
├── conftest.py              # Root pytest configuration
└── __init__.py
```

**Pytest Markers** (`pyproject.toml`):

```toml
[tool.pytest.ini_options]
markers = [
    "unit: marks tests as unit tests (fast, no external dependencies)",
    "integration: marks tests as integration tests (require external services)",
    "redteam: marks tests as red team security tests",
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

**Running Tests:**

```bash
# All tests with coverage enforcement
make test
# → pytest --cov=src --cov-fail-under=80

# Unit tests only (fast, run during development)
make test-unit
# → pytest -m unit

# Integration tests only
make test-integration
# → pytest -m integration

# Security tests only
make test-redteam
# → pytest -m redteam

# Fast tests (exclude slow tests)
make test-fast
# → pytest -m "not slow"

# Watch mode (auto-run on file changes)
make test-watch
# → pytest-watch
```

**Example Test Files:**

**Unit Test** (`tests/unit/test_auth.py`):

```python
import pytest
from src.utils.auth import get_password_hash, verify_password

@pytest.mark.unit
class TestPasswordHashing:
    def test_password_hashing(self):
        """Test that passwords are hashed correctly"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
```

**Integration Test** (`tests/integration/test_database.py`):

```python
import pytest
from src.db.connection import check_db_connection

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection():
    """Test that database connection works"""
    is_healthy = await check_db_connection()
    assert is_healthy is True
```

**Redteam Test** (`tests/redteam/test_auth_security.py`):

```python
import pytest
from pydantic import ValidationError
from src.schemas.user import UserCreate

@pytest.mark.redteam
class TestPasswordStrengthEnforcement:
    def test_common_passwords_rejected(self):
        """Test that common passwords are rejected"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="password",  # Too weak
            )
```

**Key Guidelines:**

**Unit Tests:**

- ✅ No external dependencies (database, Redis, APIs, file system)
- ✅ Fast (milliseconds per test)
- ✅ Test pure functions, business logic, validation
- ✅ Mock external dependencies
- ❌ No network calls
- ❌ No database queries

**Integration Tests:**

- ✅ Test interactions with external systems
- ✅ Require Docker services running (`make dev-services`)
- ✅ Test database queries, Redis operations, API endpoints
- ✅ Can be slower (seconds per test acceptable)
- ❌ Don't test third-party library internals

**Redteam Tests:**

- ✅ Test security vulnerabilities (SQL injection, XSS, CSRF)
- ✅ Test authentication/authorization bypasses
- ✅ Test input validation edge cases
- ✅ Document security assumptions
- ❌ Don't test known vulnerabilities in dependencies (use `bandit` instead)

**Fixture Tests:**

- Not tests themselves, just shared data
- Used by tests in all categories
- Keep fixtures simple and well-documented

**Coverage Requirements:**

- **Minimum 80%** enforced via `--cov-fail-under=80`
- Focus on business logic and critical paths
- Security-critical code should have 100% coverage
- Allow lower coverage for:
  - Generated code
  - Third-party integrations (test at integration level)
  - Trivial getters/setters

## References

- [Pytest Documentation - Markers](https://docs.pytest.org/en/stable/example/markers.html)
- [Pytest Documentation - Good Integration Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Martin Fowler - Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Google Testing Blog - Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)

---

## Revision History

| Date       | Author       | Changes                                             |
| ---------- | ------------ | --------------------------------------------------- |
| 2025-11-14 | Project Lead | Initial ADR documenting test organization structure |
