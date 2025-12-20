"""
Validation Cache Service for Claims Validation Engine.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides specialized caching for validation results, crosswalk lookups,
and LLM settings with HIPAA-compliant TTL management.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, TypeVar

from redis.asyncio import Redis

from src.api.config import settings
from src.core.config import get_claims_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheKeyPrefix(str, Enum):
    """Cache key prefixes for different data types."""

    VALIDATION_RESULT = "val"
    CROSSWALK = "xwalk"
    PROVIDER = "prov"
    POLICY = "pol"
    LLM_SETTINGS = "llm"
    ICD10_CODE = "icd"
    CPT_CODE = "cpt"
    NCCI_EDIT = "ncci"
    MUE_LIMIT = "mue"
    MEMBER = "member"
    FORENSICS = "forensics"


@dataclass
class CacheEntry:
    """Wrapper for cached data with metadata."""

    data: Any
    cached_at: str
    ttl_seconds: int
    hit_count: int = 0
    source: str = "cache"


class ValidationCacheService:
    """
    Specialized cache service for validation engine.

    Provides:
    - Type-safe caching with defined key patterns
    - Configurable TTL per data type
    - Cache statistics and monitoring
    - HIPAA-compliant data handling
    """

    # TTL configurations (in seconds) per data type
    # Source: Design Document Q3 Decision - 5 min cache then persist
    DEFAULT_TTLS = {
        CacheKeyPrefix.VALIDATION_RESULT: 300,    # 5 minutes (Q3 decision)
        CacheKeyPrefix.CROSSWALK: 3600,           # 1 hour
        CacheKeyPrefix.PROVIDER: 1800,            # 30 minutes
        CacheKeyPrefix.POLICY: 900,               # 15 minutes
        CacheKeyPrefix.LLM_SETTINGS: 600,         # 10 minutes
        CacheKeyPrefix.ICD10_CODE: 86400,         # 24 hours (static data)
        CacheKeyPrefix.CPT_CODE: 86400,           # 24 hours (static data)
        CacheKeyPrefix.NCCI_EDIT: 86400,          # 24 hours (static data)
        CacheKeyPrefix.MUE_LIMIT: 86400,          # 24 hours (static data)
        CacheKeyPrefix.MEMBER: 900,               # 15 minutes
        CacheKeyPrefix.FORENSICS: 3600,           # 1 hour (document analysis)
    }

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the validation cache service.

        Args:
            redis_url: Redis connection URL. If not provided, uses settings.
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[Redis] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = Redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Validation cache connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Validation cache disconnected from Redis")

    @property
    def redis(self) -> Redis:
        """Get Redis client, raising if not connected."""
        if self._redis is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._redis

    # =========================================================================
    # Key Generation
    # =========================================================================

    def _build_key(self, prefix: CacheKeyPrefix, *parts: str) -> str:
        """
        Build a cache key from prefix and parts.

        Args:
            prefix: Key prefix enum
            *parts: Key components

        Returns:
            Formatted cache key
        """
        return f"{prefix.value}:{':'.join(parts)}"

    # =========================================================================
    # Validation Result Caching
    # =========================================================================

    async def get_validation_result(
        self,
        claim_id: str,
        rule_id: str,
    ) -> Optional[dict]:
        """
        Get cached validation result for a claim/rule pair.

        Args:
            claim_id: Claim identifier
            rule_id: Validation rule identifier

        Returns:
            Cached validation result or None
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.VALIDATION_RESULT, claim_id, rule_id)
        return await self._get(key)

    async def set_validation_result(
        self,
        claim_id: str,
        rule_id: str,
        result: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache a validation result.

        Args:
            claim_id: Claim identifier
            rule_id: Validation rule identifier
            result: Validation result to cache
            ttl: Optional TTL override
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.VALIDATION_RESULT, claim_id, rule_id)
        ttl = ttl or self.DEFAULT_TTLS[CacheKeyPrefix.VALIDATION_RESULT]
        await self._set(key, result, ttl)

    async def get_all_validation_results(
        self,
        claim_id: str,
    ) -> dict[str, dict]:
        """
        Get all cached validation results for a claim.

        Args:
            claim_id: Claim identifier

        Returns:
            Dict mapping rule_id to validation result
        """
        await self.connect()
        pattern = self._build_key(CacheKeyPrefix.VALIDATION_RESULT, claim_id, "*")
        results = {}

        async for key in self.redis.scan_iter(match=pattern):
            rule_id = key.split(":")[-1]
            result = await self._get(key)
            if result:
                results[rule_id] = result

        return results

    async def invalidate_claim_cache(self, claim_id: str) -> int:
        """
        Invalidate all cached data for a claim.

        Args:
            claim_id: Claim identifier

        Returns:
            Number of keys deleted
        """
        await self.connect()
        pattern = self._build_key(CacheKeyPrefix.VALIDATION_RESULT, claim_id, "*")
        return await self._delete_pattern(pattern)

    # =========================================================================
    # Crosswalk Caching
    # =========================================================================

    async def get_crosswalk(
        self,
        icd_code: str,
        cpt_code: str,
    ) -> Optional[dict]:
        """
        Get cached ICD-CPT crosswalk result.

        Args:
            icd_code: ICD-10 code
            cpt_code: CPT code

        Returns:
            Cached crosswalk result or None
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.CROSSWALK, icd_code, cpt_code)
        return await self._get(key)

    async def set_crosswalk(
        self,
        icd_code: str,
        cpt_code: str,
        result: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache an ICD-CPT crosswalk result.

        Args:
            icd_code: ICD-10 code
            cpt_code: CPT code
            result: Crosswalk result
            ttl: Optional TTL override
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.CROSSWALK, icd_code, cpt_code)
        ttl = ttl or self.DEFAULT_TTLS[CacheKeyPrefix.CROSSWALK]
        await self._set(key, result, ttl)

    # =========================================================================
    # Provider Caching
    # =========================================================================

    async def get_provider(self, npi: str) -> Optional[dict]:
        """
        Get cached provider data by NPI.

        Args:
            npi: National Provider Identifier

        Returns:
            Cached provider data or None
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.PROVIDER, npi)
        return await self._get(key)

    async def set_provider(
        self,
        npi: str,
        provider_data: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache provider data.

        Args:
            npi: National Provider Identifier
            provider_data: Provider information
            ttl: Optional TTL override
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.PROVIDER, npi)
        ttl = ttl or self.DEFAULT_TTLS[CacheKeyPrefix.PROVIDER]
        await self._set(key, provider_data, ttl)

    # =========================================================================
    # Policy Caching
    # =========================================================================

    async def get_policy(
        self,
        member_id: str,
        policy_id: str,
    ) -> Optional[dict]:
        """
        Get cached policy data.

        Args:
            member_id: Member identifier
            policy_id: Policy identifier

        Returns:
            Cached policy data or None
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.POLICY, member_id, policy_id)
        return await self._get(key)

    async def set_policy(
        self,
        member_id: str,
        policy_id: str,
        policy_data: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache policy data.

        Args:
            member_id: Member identifier
            policy_id: Policy identifier
            policy_data: Policy information
            ttl: Optional TTL override
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.POLICY, member_id, policy_id)
        ttl = ttl or self.DEFAULT_TTLS[CacheKeyPrefix.POLICY]
        await self._set(key, policy_data, ttl)

    # =========================================================================
    # LLM Settings Caching
    # =========================================================================

    async def get_llm_settings(
        self,
        tenant_id: str,
        task_type: str,
    ) -> Optional[dict]:
        """
        Get cached LLM settings for a tenant/task.

        Args:
            tenant_id: Tenant identifier
            task_type: Task type (extraction, validation, etc.)

        Returns:
            Cached LLM settings or None
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.LLM_SETTINGS, tenant_id, task_type)
        return await self._get(key)

    async def set_llm_settings(
        self,
        tenant_id: str,
        task_type: str,
        settings_data: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache LLM settings.

        Args:
            tenant_id: Tenant identifier
            task_type: Task type
            settings_data: LLM configuration
            ttl: Optional TTL override
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.LLM_SETTINGS, tenant_id, task_type)
        ttl = ttl or self.DEFAULT_TTLS[CacheKeyPrefix.LLM_SETTINGS]
        await self._set(key, settings_data, ttl)

    async def invalidate_llm_settings(self, tenant_id: str) -> int:
        """
        Invalidate all LLM settings for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Number of keys deleted
        """
        await self.connect()
        pattern = self._build_key(CacheKeyPrefix.LLM_SETTINGS, tenant_id, "*")
        return await self._delete_pattern(pattern)

    # =========================================================================
    # Medical Code Caching (for frequently accessed codes)
    # =========================================================================

    async def get_icd10_code(self, code: str) -> Optional[dict]:
        """Get cached ICD-10 code data."""
        await self.connect()
        key = self._build_key(CacheKeyPrefix.ICD10_CODE, code)
        return await self._get(key)

    async def set_icd10_code(self, code: str, data: dict) -> None:
        """Cache ICD-10 code data."""
        await self.connect()
        key = self._build_key(CacheKeyPrefix.ICD10_CODE, code)
        await self._set(key, data, self.DEFAULT_TTLS[CacheKeyPrefix.ICD10_CODE])

    async def get_cpt_code(self, code: str) -> Optional[dict]:
        """Get cached CPT code data."""
        await self.connect()
        key = self._build_key(CacheKeyPrefix.CPT_CODE, code)
        return await self._get(key)

    async def set_cpt_code(self, code: str, data: dict) -> None:
        """Cache CPT code data."""
        await self.connect()
        key = self._build_key(CacheKeyPrefix.CPT_CODE, code)
        await self._set(key, data, self.DEFAULT_TTLS[CacheKeyPrefix.CPT_CODE])

    # =========================================================================
    # Forensics Result Caching
    # =========================================================================

    async def get_forensics_result(
        self,
        document_hash: str,
    ) -> Optional[dict]:
        """
        Get cached forensics analysis result.

        Args:
            document_hash: Hash of the document

        Returns:
            Cached forensics result or None
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.FORENSICS, document_hash)
        return await self._get(key)

    async def set_forensics_result(
        self,
        document_hash: str,
        result: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache forensics analysis result.

        Args:
            document_hash: Hash of the document
            result: Forensics analysis result
            ttl: Optional TTL override
        """
        await self.connect()
        key = self._build_key(CacheKeyPrefix.FORENSICS, document_hash)
        ttl = ttl or self.DEFAULT_TTLS[CacheKeyPrefix.FORENSICS]
        await self._set(key, result, ttl)

    # =========================================================================
    # Core Cache Operations
    # =========================================================================

    async def _get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        value = await self.redis.get(key)
        if value:
            self._stats["hits"] += 1
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        self._stats["misses"] += 1
        return None

    async def _set(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        self._stats["sets"] += 1
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis.setex(key, ttl, value)

    async def _delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern

        Returns:
            Number of keys deleted
        """
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            deleted = await self.redis.delete(*keys)
            self._stats["deletes"] += deleted
            return deleted
        return 0

    # =========================================================================
    # Statistics and Monitoring
    # =========================================================================

    @property
    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        stats = self._stats.copy()
        total = stats["hits"] + stats["misses"]
        stats["hit_rate"] = (stats["hits"] / total * 100) if total > 0 else 0.0
        return stats

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on Redis connection.

        Returns:
            Health status dict
        """
        try:
            await self.connect()
            await self.redis.ping()
            info = await self.redis.info("memory")
            return {
                "healthy": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "stats": self.stats,
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }


# Singleton instance
_validation_cache: Optional[ValidationCacheService] = None


def get_validation_cache() -> ValidationCacheService:
    """Get or create the singleton validation cache instance."""
    global _validation_cache
    if _validation_cache is None:
        _validation_cache = ValidationCacheService()
    return _validation_cache


async def initialize_validation_cache() -> ValidationCacheService:
    """Initialize and return the validation cache."""
    cache = get_validation_cache()
    await cache.connect()
    return cache
