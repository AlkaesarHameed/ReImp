"""
Redis Cache Service
High-performance caching layer
Source: https://redis.io/docs/connect/clients/python/
Verified: 2025-11-14
"""

import json
from typing import Any

from redis.asyncio import Redis

from src.api.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Redis cache service for application-wide caching.

    Evidence: Redis for caching improves performance and reduces database load
    Source: https://redis.io/docs/manual/patterns/twitter-clone/
    Verified: 2025-11-14
    """

    def __init__(self):
        self._redis: Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis"""
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Warm-up ping ensures credentials/network are valid
            await self._redis.ping()
            logger.info("Connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (JSON-decoded) or None if not found
        """
        if not self._redis:
            await self.connect()

        value = await self._redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON-encoded)
            ttl: Time to live in seconds (default: from settings)
        """
        if not self._redis:
            await self.connect()

        ttl = ttl or settings.CACHE_TTL

        # Serialize value
        if isinstance(value, dict | list):
            value = json.dumps(value)

        await self._redis.setex(key, ttl, value)

    async def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        if not self._redis:
            await self.connect()

        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._redis:
            await self.connect()

        return bool(await self._redis.exists(key))

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self._redis:
            await self.connect()

        keys = []
        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            return await self._redis.delete(*keys)
        return 0


# Global cache instance
cache = CacheService()
