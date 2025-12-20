"""
Alembic Environment Configuration
Async SQLAlchemy with multi-tenant support.

Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
Verified: 2025-12-18
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models to ensure they're registered with Base
from src.models.base import Base

# Import all models here so Alembic can detect them
from src.models.user import User  # noqa: F401
from src.models.document import Document  # noqa: F401

# Import new domain models (will be created)
# from src.models.tenant import Tenant  # noqa: F401
# from src.models.claim import Claim  # noqa: F401
# from src.models.policy import Policy  # noqa: F401
# from src.models.provider import HealthcareProvider  # noqa: F401
# from src.models.member import Member  # noqa: F401
# from src.models.audit import AuditLog  # noqa: F401

# Config object provides access to .ini file values
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """
    Get database URL from environment.

    Returns:
        Database connection URL

    Note: In production, this should be loaded from environment variables
    """
    import os

    # Try to get from environment first
    url = os.getenv("DATABASE_URL")
    if url:
        # Convert postgres:// to postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Fallback to config settings
    try:
        from src.api.config import settings

        return settings.database_url
    except Exception:
        # Default for migrations
        return "postgresql+asyncpg://starter_user:starter_pass@localhost:5432/starter_db"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit SQL to the script output.

    Source: https://alembic.sqlalchemy.org/en/latest/offline.html
    Verified: 2025-12-18
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations using the provided connection.

    Args:
        connection: SQLAlchemy connection
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.

    Creates an async engine and runs migrations in a connection context.

    Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
    Verified: 2025-12-18
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an async Engine and associates a connection with the context.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
