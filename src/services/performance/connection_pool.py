"""
Connection Pool Service.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides connection pooling for database and external services.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PoolStatus(str, Enum):
    """Connection pool status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ConnectionState(str, Enum):
    """Connection state."""

    IDLE = "idle"
    IN_USE = "in_use"
    CLOSED = "closed"
    ERROR = "error"


class PoolConfig(BaseModel):
    """Connection pool configuration."""

    min_size: int = 5
    max_size: int = 20
    max_idle_time: int = 300  # seconds
    max_lifetime: int = 3600  # seconds
    acquire_timeout: float = 30.0  # seconds
    health_check_interval: int = 60  # seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds


class PoolStats(BaseModel):
    """Connection pool statistics."""

    total_connections: int = 0
    idle_connections: int = 0
    in_use_connections: int = 0
    pending_requests: int = 0
    total_acquisitions: int = 0
    total_releases: int = 0
    failed_acquisitions: int = 0
    avg_acquire_time_ms: float = 0.0
    avg_use_time_ms: float = 0.0
    status: PoolStatus = PoolStatus.HEALTHY


class ConnectionInfo(BaseModel):
    """Connection metadata."""

    connection_id: str = Field(default_factory=lambda: str(uuid4()))
    state: ConnectionState = ConnectionState.IDLE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    last_error: Optional[str] = None


T = TypeVar("T")


class PooledConnection(Generic[T]):
    """Wrapper for pooled connection."""

    def __init__(
        self,
        connection: T,
        info: ConnectionInfo,
        pool: "ConnectionPool[T]",
    ):
        """Initialize pooled connection."""
        self._connection = connection
        self._info = info
        self._pool = pool
        self._acquired_at = time.perf_counter()

    @property
    def connection(self) -> T:
        """Get underlying connection."""
        return self._connection

    @property
    def info(self) -> ConnectionInfo:
        """Get connection info."""
        return self._info

    async def release(self) -> None:
        """Release connection back to pool."""
        await self._pool.release(self)

    def __enter__(self) -> T:
        """Context manager entry."""
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        asyncio.create_task(self.release())


class ConnectionPool(Generic[T]):
    """Generic connection pool implementation."""

    def __init__(
        self,
        factory: Any,  # Callable that creates connections
        config: PoolConfig | None = None,
    ):
        """Initialize connection pool.

        Args:
            factory: Async callable that creates new connections
            config: Pool configuration
        """
        self._factory = factory
        self._config = config or PoolConfig()

        self._connections: dict[str, tuple[T, ConnectionInfo]] = {}
        self._idle_queue: asyncio.Queue[str] = asyncio.Queue()
        self._pending_count = 0
        self._lock = asyncio.Lock()
        self._closed = False

        # Statistics
        self._total_acquisitions = 0
        self._total_releases = 0
        self._failed_acquisitions = 0
        self._acquire_times: list[float] = []
        self._use_times: list[float] = []

    @property
    def config(self) -> PoolConfig:
        """Get pool configuration."""
        return self._config

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        for _ in range(self._config.min_size):
            try:
                conn, info = await self._create_connection()
                self._connections[info.connection_id] = (conn, info)
                await self._idle_queue.put(info.connection_id)
            except Exception:
                pass  # Continue with fewer connections

    async def _create_connection(self) -> tuple[T, ConnectionInfo]:
        """Create a new connection."""
        if asyncio.iscoroutinefunction(self._factory):
            connection = await self._factory()
        else:
            connection = self._factory()

        info = ConnectionInfo(state=ConnectionState.IDLE)
        return connection, info

    async def acquire(self) -> PooledConnection[T]:
        """Acquire a connection from the pool."""
        start = time.perf_counter()
        self._pending_count += 1

        try:
            # Try to get from idle queue
            try:
                conn_id = await asyncio.wait_for(
                    self._idle_queue.get(),
                    timeout=0.1,  # Quick check
                )

                if conn_id in self._connections:
                    conn, info = self._connections[conn_id]

                    # Validate connection
                    if self._is_connection_valid(info):
                        info.state = ConnectionState.IN_USE
                        info.last_used_at = datetime.utcnow()
                        info.use_count += 1

                        self._total_acquisitions += 1
                        self._acquire_times.append((time.perf_counter() - start) * 1000)

                        return PooledConnection(conn, info, self)

                    # Connection invalid, remove and try again
                    await self._close_connection(conn_id)

            except asyncio.TimeoutError:
                pass  # No idle connection available

            # Try to create new connection if under max
            async with self._lock:
                if len(self._connections) < self._config.max_size:
                    conn, info = await self._create_connection()
                    info.state = ConnectionState.IN_USE
                    info.last_used_at = datetime.utcnow()
                    info.use_count = 1

                    self._connections[info.connection_id] = (conn, info)
                    self._total_acquisitions += 1
                    self._acquire_times.append((time.perf_counter() - start) * 1000)

                    return PooledConnection(conn, info, self)

            # Wait for available connection
            for _ in range(self._config.retry_attempts):
                try:
                    conn_id = await asyncio.wait_for(
                        self._idle_queue.get(),
                        timeout=self._config.acquire_timeout / self._config.retry_attempts,
                    )

                    if conn_id in self._connections:
                        conn, info = self._connections[conn_id]
                        info.state = ConnectionState.IN_USE
                        info.last_used_at = datetime.utcnow()
                        info.use_count += 1

                        self._total_acquisitions += 1
                        self._acquire_times.append((time.perf_counter() - start) * 1000)

                        return PooledConnection(conn, info, self)

                except asyncio.TimeoutError:
                    await asyncio.sleep(self._config.retry_delay)

            # Failed to acquire
            self._failed_acquisitions += 1
            raise TimeoutError("Failed to acquire connection from pool")

        finally:
            self._pending_count -= 1

    async def release(self, pooled: PooledConnection[T]) -> None:
        """Release a connection back to the pool."""
        use_time = (time.perf_counter() - pooled._acquired_at) * 1000
        self._use_times.append(use_time)
        self._total_releases += 1

        info = pooled.info
        info.state = ConnectionState.IDLE

        if self._is_connection_valid(info):
            await self._idle_queue.put(info.connection_id)
        else:
            # Connection expired, close it
            await self._close_connection(info.connection_id)

            # Create replacement if below minimum
            async with self._lock:
                if len(self._connections) < self._config.min_size:
                    try:
                        conn, new_info = await self._create_connection()
                        self._connections[new_info.connection_id] = (conn, new_info)
                        await self._idle_queue.put(new_info.connection_id)
                    except Exception:
                        pass

    def _is_connection_valid(self, info: ConnectionInfo) -> bool:
        """Check if connection is still valid."""
        now = datetime.utcnow()

        # Check lifetime
        age = (now - info.created_at).total_seconds()
        if age > self._config.max_lifetime:
            return False

        # Check idle time
        if info.last_used_at:
            idle = (now - info.last_used_at).total_seconds()
            if idle > self._config.max_idle_time:
                return False

        # Check error state
        if info.state == ConnectionState.ERROR:
            return False

        return True

    async def _close_connection(self, conn_id: str) -> None:
        """Close and remove a connection."""
        async with self._lock:
            if conn_id in self._connections:
                conn, info = self._connections.pop(conn_id)
                info.state = ConnectionState.CLOSED

                # Try to close gracefully
                if hasattr(conn, "close"):
                    try:
                        if asyncio.iscoroutinefunction(conn.close):
                            await conn.close()
                        else:
                            conn.close()
                    except Exception:
                        pass

    @asynccontextmanager
    async def connection(self):
        """Context manager for acquiring a connection."""
        pooled = await self.acquire()
        try:
            yield pooled.connection
        finally:
            await pooled.release()

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        total = len(self._connections)
        idle = self._idle_queue.qsize()
        in_use = total - idle

        # Determine status
        if total == 0:
            status = PoolStatus.UNHEALTHY
        elif in_use / max(total, 1) > 0.9:
            status = PoolStatus.DEGRADED
        else:
            status = PoolStatus.HEALTHY

        avg_acquire = (
            sum(self._acquire_times[-100:]) / len(self._acquire_times[-100:])
            if self._acquire_times else 0.0
        )
        avg_use = (
            sum(self._use_times[-100:]) / len(self._use_times[-100:])
            if self._use_times else 0.0
        )

        return PoolStats(
            total_connections=total,
            idle_connections=idle,
            in_use_connections=in_use,
            pending_requests=self._pending_count,
            total_acquisitions=self._total_acquisitions,
            total_releases=self._total_releases,
            failed_acquisitions=self._failed_acquisitions,
            avg_acquire_time_ms=avg_acquire,
            avg_use_time_ms=avg_use,
            status=status,
        )

    async def close(self) -> None:
        """Close all connections and shut down pool."""
        self._closed = True

        for conn_id in list(self._connections.keys()):
            await self._close_connection(conn_id)

    async def health_check(self) -> bool:
        """Perform health check on pool."""
        stats = self.get_stats()
        return stats.status != PoolStatus.UNHEALTHY


# =============================================================================
# Factory Functions
# =============================================================================


_connection_pools: dict[str, ConnectionPool] = {}


def get_connection_pool(
    name: str = "default",
    factory: Any = None,
    config: PoolConfig | None = None,
) -> ConnectionPool:
    """Get or create a named connection pool."""
    global _connection_pools

    if name not in _connection_pools:
        if factory is None:
            raise ValueError(f"No factory provided for new pool: {name}")
        _connection_pools[name] = ConnectionPool(factory, config)

    return _connection_pools[name]


def create_connection_pool(
    factory: Any,
    config: PoolConfig | None = None,
) -> ConnectionPool:
    """Create a new connection pool."""
    return ConnectionPool(factory, config)
