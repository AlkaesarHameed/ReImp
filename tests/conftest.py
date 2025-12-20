"""
Pytest Configuration and Fixtures.
Shared test fixtures for all test modules.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_user_data():
    """Create mock user data for testing."""
    return {
        "id": str(uuid4()),
        "email": "test@claims.local",
        "username": "testuser",
        "full_name": "Test User",
        "is_active": True,
        "is_verified": True,
        "is_superuser": False,
    }


@pytest.fixture
def mock_admin_data():
    """Create mock admin user data for testing."""
    return {
        "id": str(uuid4()),
        "email": "admin@claims.local",
        "username": "admin",
        "full_name": "System Administrator",
        "is_active": True,
        "is_verified": True,
        "is_superuser": True,
    }


@pytest.fixture
def mock_claim_data():
    """Create mock claim data for testing."""
    return {
        "id": str(uuid4()),
        "claim_number": f"CLM-{uuid4().hex[:8].upper()}",
        "patient_id": str(uuid4()),
        "provider_id": str(uuid4()),
        "payer_id": str(uuid4()),
        "type": "professional",
        "status": "submitted",
        "priority": "normal",
        "total_charge": 1500.00,
        "service_date": "2024-01-15",
    }


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# Configure pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as an API test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security-related"
    )
