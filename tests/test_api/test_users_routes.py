"""API tests for user routes.
Ensures /users endpoints enforce correct permissions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.deps import get_current_active_user, get_current_superuser
from src.api.main import app
from src.db.connection import get_session
from src.utils.errors import AuthenticationError

client = TestClient(app)


def _build_user(*, is_superuser: bool = False) -> SimpleNamespace:
    """Create a simple user-like object for dependency overrides."""
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        username="user",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        is_superuser=is_superuser,
        created_at=now,
        updated_at=now,
        last_login=now,
    )


class _DummyResult:
    def __init__(self, user: SimpleNamespace):
        self._user = user

    def scalar_one_or_none(self) -> SimpleNamespace | None:
        return self._user


class _DummySession:
    def __init__(self, user: SimpleNamespace):
        self._user = user

    async def execute(self, *_args, **_kwargs):
        return _DummyResult(self._user)

    async def close(self) -> None:  # pragma: no cover - required for context cleanup
        return None


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """Ensure dependency overrides are isolated per test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_get_current_user_profile_returns_profile():
    """GET /users/me should return the current active user profile."""
    current_user = _build_user()
    app.dependency_overrides[get_current_active_user] = lambda: current_user

    response = client.get("/users/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(current_user.id)
    assert payload["email"] == current_user.email


def test_admin_can_fetch_user_by_id():
    """GET /users/{id} should return data when requester is a superuser."""
    admin = _build_user(is_superuser=True)
    target_user = _build_user()

    async def override_get_session():
        yield _DummySession(target_user)

    app.dependency_overrides[get_current_superuser] = lambda: admin
    app.dependency_overrides[get_session] = override_get_session

    response = client.get(f"/users/{target_user.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(target_user.id)
    assert payload["email"] == target_user.email


def test_non_superuser_request_is_denied():
    """GET /users/{id} should fail when dependency rejects the requester."""

    def deny_access():
        raise AuthenticationError("Superuser access required")

    async def override_get_session():
        yield _DummySession(_build_user())

    app.dependency_overrides[get_current_superuser] = deny_access
    app.dependency_overrides[get_session] = override_get_session

    response = client.get(f"/users/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Superuser access required"
