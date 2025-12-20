"""
Integration Tests for Database Operations
Tests actual database connections and queries
"""

import pytest
from sqlalchemy import text

from src.db.connection import (
    check_db_connection,
    get_engine,
    get_session_maker,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection():
    """Test that database connection works"""
    is_healthy = await check_db_connection()
    assert is_healthy is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_query():
    """Test basic database query"""
    session_maker = get_session_maker()

    async with session_maker() as session:
        result = await session.execute(text("SELECT 1 as num"))
        row = result.first()
        assert row[0] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_transaction():
    """Test database transaction rollback"""
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            # Execute a query
            await session.execute(text("SELECT 1"))
            # Rollback should not raise error
            await session.rollback()
        except Exception as e:
            pytest.fail(f"Transaction rollback failed: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_pool_size():
    """Test that connection pool is configured"""
    engine = get_engine()
    assert engine is not None
    # Pool should be configured (not NullPool in non-testing environment)
    assert hasattr(engine.pool, "size")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_multiple_concurrent_connections():
    """Test that multiple concurrent database connections work"""
    session_maker = get_session_maker()

    async def query():
        async with session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar()

    # Run 10 concurrent queries
    import asyncio

    results = await asyncio.gather(*[query() for _ in range(10)])

    # All should succeed
    assert all(r == 1 for r in results)
    assert len(results) == 10
