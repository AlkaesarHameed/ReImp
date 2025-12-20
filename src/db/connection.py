"""
Database Connection Management
Async SQLAlchemy with connection pooling
Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
Verified: 2025-11-14
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.api.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Global engine instance
# Evidence: Singleton pattern for database engine
# Source: SQLAlchemy best practices
# https://docs.sqlalchemy.org/en/20/core/pooling.html#pooling-plain
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global async engine.

    Returns:
        AsyncEngine instance

    Evidence: Engine should be created once and reused
    Source: https://docs.sqlalchemy.org/en/20/core/connections.html#basic-usage
    Verified: 2025-11-14
    """
    global _engine

    if _engine is None:
        logger.info(f"Creating database engine: {settings.database_url.split('@')[-1]}")

        # Engine configuration
        # Source: https://docs.sqlalchemy.org/en/20/core/engines.html#engine-configuration
        # Evidence: NullPool does not accept pool_size/max_overflow/pool_timeout parameters
        # Source: https://docs.sqlalchemy.org/en/20/core/pooling.html
        # Verified: 2025-11-14
        if settings.is_testing:
            # NullPool for testing: no connection pooling, no pool parameters
            # Creates/closes connection per request to avoid connection leaks
            _engine = create_async_engine(
                settings.database_url,
                echo=settings.DEBUG,  # Log SQL in debug mode
                poolclass=NullPool,
            )
        else:
            # QueuePool (default) for production: supports pooling parameters
            _engine = create_async_engine(
                settings.database_url,
                echo=settings.DEBUG,  # Log SQL in debug mode
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_pre_ping=True,  # Verify connections before using
            )

        logger.info("Database engine created successfully")

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the global session maker.

    Returns:
        Async session maker

    Evidence: Session maker should be created once and reused
    Source: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
    Verified: 2025-11-14
    """
    global _async_session_maker

    if _async_session_maker is None:
        engine = get_engine()

        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flush control
            autocommit=False,  # Explicit transaction management
        )

        logger.info("Session maker created successfully")

    return _async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.

    Yields:
        AsyncSession instance

    Example:
        >>> from fastapi import Depends
        >>> from src.db.connection import get_session
        >>>
        >>> @app.get("/users")
        >>> async def get_users(session: AsyncSession = Depends(get_session)):
        >>>     result = await session.execute(select(User))
        >>>     return result.scalars().all()

    Evidence: Dependency injection pattern for FastAPI
    Source: https://fastapi.tiangolo.com/tutorial/sql-databases/#create-a-dependency
    Verified: 2025-11-14
    """
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def close_db_connection() -> None:
    """
    Close database connection pool.

    Evidence: Cleanup function for application shutdown
    Source: https://fastapi.tiangolo.com/advanced/events/#shutdown-event
    Verified: 2025-11-14
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("Closing database connection pool...")
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("Database connection pool closed")


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if connection is healthy, False otherwise

    Evidence: Health check for monitoring
    Source: PostgreSQL pg_isready equivalent
    Verified: 2025-11-14

    Note: Uses text() construct for SQL safety (SQLAlchemy 2.0+)
    Source: https://docs.sqlalchemy.org/en/20/core/connections.html#using-textual-sql
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
