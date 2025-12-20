"""
Caching Service.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides multi-tier caching with Redis and in-memory fallback.
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Generic

from pydantic import BaseModel, Field


class CacheBackend(str, Enum):
    """Cache backend types."""

    MEMORY = "memory"
    REDIS = "redis"
    TIERED = "tiered"  # Memory + Redis


class CacheConfig(BaseModel):
    """Cache configuration."""

    backend: CacheBackend = CacheBackend.MEMORY
    default_ttl: int = 300  # seconds
    max_memory_items: int = 1000
    redis_url: Optional[str] = None
    key_prefix: str = "reimp:"
    compression_threshold: int = 1024  # bytes


class CacheStats(BaseModel):
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_items: int = 0
    memory_usage_bytes: int = 0
    hit_rate: float = 0.0
    avg_get_time_ms: float = 0.0
    avg_set_time_ms: float = 0.0


class CacheEntry(BaseModel):
    """Single cache entry."""

    key: str
    value: Any
    ttl: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.utcnow() > self.expires_at


class LRUCache:
    """Least Recently Used cache implementation."""

    def __init__(self, max_size: int = 1000):
        """Initialize LRU cache."""
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
    ) -> None:
        """Set value in cache."""
        async with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            now = datetime.utcnow()
            from datetime import timedelta

            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl),
            )

            self._cache[key] = entry
            self._cache.move_to_end(key)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        async with self._lock:
            if pattern == "*":
                return list(self._cache.keys())

            import fnmatch

            return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class CacheService:
    """Multi-tier caching service."""

    def __init__(self, config: CacheConfig | None = None):
        """Initialize CacheService."""
        self._config = config or CacheConfig()
        self._memory_cache = LRUCache(self._config.max_memory_items)
        self._redis_client: Any = None

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._get_times: list[float] = []
        self._set_times: list[float] = []

    @property
    def config(self) -> CacheConfig:
        """Get cache configuration."""
        return self._config

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self._config.key_prefix}{key}"

    def _hash_key(self, data: dict | list) -> str:
        """Create hash key from complex data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        start = time.perf_counter()
        full_key = self._make_key(key)

        # Try memory cache first
        value = await self._memory_cache.get(full_key)

        if value is not None:
            self._hits += 1
            self._get_times.append((time.perf_counter() - start) * 1000)
            return value

        # For tiered backend, try Redis
        if self._config.backend == CacheBackend.TIERED and self._redis_client:
            try:
                redis_value = await self._redis_client.get(full_key)
                if redis_value:
                    value = json.loads(redis_value)
                    # Populate memory cache
                    await self._memory_cache.set(full_key, value, self._config.default_ttl)
                    self._hits += 1
                    self._get_times.append((time.perf_counter() - start) * 1000)
                    return value
            except Exception:
                pass  # Redis unavailable, continue without

        self._misses += 1
        self._get_times.append((time.perf_counter() - start) * 1000)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache."""
        start = time.perf_counter()
        full_key = self._make_key(key)
        cache_ttl = ttl or self._config.default_ttl

        # Set in memory cache
        await self._memory_cache.set(full_key, value, cache_ttl)

        # For tiered backend, also set in Redis
        if self._config.backend == CacheBackend.TIERED and self._redis_client:
            try:
                serialized = json.dumps(value, default=str)
                await self._redis_client.setex(full_key, cache_ttl, serialized)
            except Exception:
                pass  # Redis unavailable, memory cache still works

        self._set_times.append((time.perf_counter() - start) * 1000)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        full_key = self._make_key(key)
        deleted = await self._memory_cache.delete(full_key)

        if self._config.backend == CacheBackend.TIERED and self._redis_client:
            try:
                await self._redis_client.delete(full_key)
            except Exception:
                pass

        return deleted

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        full_pattern = self._make_key(pattern)
        keys = await self._memory_cache.keys(full_pattern)
        count = 0

        for key in keys:
            if await self._memory_cache.delete(key):
                count += 1

        return count

    async def clear(self) -> None:
        """Clear all cache entries."""
        await self._memory_cache.clear()

        if self._config.backend == CacheBackend.TIERED and self._redis_client:
            try:
                keys = await self._redis_client.keys(f"{self._config.key_prefix}*")
                if keys:
                    await self._redis_client.delete(*keys)
            except Exception:
                pass

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: int | None = None,
    ) -> Any:
        """Get from cache or compute and set."""
        value = await self.get(key)

        if value is None:
            # Compute value
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()

            await self.set(key, value, ttl)

        return value

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        avg_get = sum(self._get_times[-100:]) / len(self._get_times[-100:]) if self._get_times else 0.0
        avg_set = sum(self._set_times[-100:]) / len(self._set_times[-100:]) if self._set_times else 0.0

        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            total_items=self._memory_cache.size(),
            memory_usage_bytes=0,  # Would need sys.getsizeof for accurate
            hit_rate=hit_rate,
            avg_get_time_ms=avg_get,
            avg_set_time_ms=avg_set,
        )

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._get_times.clear()
        self._set_times.clear()


# =============================================================================
# Decorator
# =============================================================================

T = TypeVar("T")


def cached(
    key_prefix: str,
    ttl: int = 300,
    cache_service: CacheService | None = None,
):
    """Decorator for caching function results.

    Args:
        key_prefix: Prefix for cache keys
        ttl: Time to live in seconds
        cache_service: Optional cache service instance
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Get or create cache service
            svc = cache_service or get_cache_service()

            # Build cache key
            key_parts = [key_prefix]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Check cache
            cached_value = await svc.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            await svc.set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For sync functions, run in event loop
            return asyncio.get_event_loop().run_until_complete(
                async_wrapper(*args, **kwargs)
            )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# Factory Functions
# =============================================================================


_cache_service: CacheService | None = None


def get_cache_service(config: CacheConfig | None = None) -> CacheService:
    """Get singleton CacheService instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(config)
    return _cache_service


def create_cache_service(config: CacheConfig | None = None) -> CacheService:
    """Create new CacheService instance."""
    return CacheService(config)
