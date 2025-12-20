"""
LLM Validation Service with Tenant-Configurable Settings.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides LLM-based validation capabilities with:
- Per-tenant provider/model configuration
- Fallback support
- Usage tracking and cost estimation
- Caching for repeated validations
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.gateways.llm_gateway import (
    LLMGateway,
    LLMRequest,
    LLMResponse,
    MessageRole,
    LLMMessage,
    get_llm_gateway,
)
from src.schemas.llm_settings import LLMProvider, LLMTaskType
from src.services.validation_cache import get_validation_cache, ValidationCacheService

logger = logging.getLogger(__name__)


# Cost per 1M tokens (approximate, as of late 2024)
COST_PER_1M_TOKENS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "ollama": {"input": 0.00, "output": 0.00},  # Local
    "vllm": {"input": 0.00, "output": 0.00},  # Self-hosted
}


@dataclass
class LLMUsageMetrics:
    """Usage metrics for an LLM call."""

    task_type: LLMTaskType
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    success: bool
    estimated_cost_usd: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TenantLLMConfig:
    """LLM configuration for a specific tenant and task."""

    tenant_id: UUID
    task_type: LLMTaskType
    provider: LLMProvider
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 4096
    fallback_provider: Optional[LLMProvider] = None
    fallback_model: Optional[str] = None
    rate_limit_rpm: int = 60


@dataclass
class ValidationLLMResult:
    """Result from an LLM validation call."""

    success: bool
    content: str
    parsed_data: Optional[dict] = None
    confidence: float = 0.0
    provider_used: str = ""
    model_used: str = ""
    latency_ms: int = 0
    error: Optional[str] = None
    usage: Optional[LLMUsageMetrics] = None


class LLMValidationService:
    """
    LLM service for validation tasks with tenant configuration.

    Supports:
    - Per-tenant LLM provider/model configuration
    - Automatic fallback on errors
    - Usage tracking and cost estimation
    - Response caching
    """

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        cache: Optional[ValidationCacheService] = None,
    ):
        """
        Initialize the LLM validation service.

        Args:
            llm_gateway: Pre-configured LLM gateway
            cache: Validation cache service
        """
        self._llm_gateway = llm_gateway
        self._cache = cache
        self._usage_buffer: list[LLMUsageMetrics] = []
        self._tenant_configs: dict[str, TenantLLMConfig] = {}

    @property
    def llm_gateway(self) -> LLMGateway:
        """Get LLM gateway instance."""
        if self._llm_gateway is None:
            self._llm_gateway = get_llm_gateway()
        return self._llm_gateway

    @property
    def cache(self) -> ValidationCacheService:
        """Get cache instance."""
        if self._cache is None:
            self._cache = get_validation_cache()
        return self._cache

    async def initialize(self) -> None:
        """Initialize the LLM gateway."""
        await self.llm_gateway.initialize()
        logger.info("LLM Validation Service initialized")

    async def get_tenant_config(
        self,
        tenant_id: UUID,
        task_type: LLMTaskType,
    ) -> Optional[TenantLLMConfig]:
        """
        Get LLM configuration for a tenant and task type.

        First checks cache, then database.
        """
        cache_key = f"{tenant_id}:{task_type.value}"

        # Check in-memory cache
        if cache_key in self._tenant_configs:
            return self._tenant_configs[cache_key]

        # Check Redis cache
        cached = await self.cache.get_llm_setting(str(tenant_id), task_type.value)
        if cached:
            config = TenantLLMConfig(
                tenant_id=tenant_id,
                task_type=task_type,
                provider=LLMProvider(cached["provider"]),
                model_name=cached["model_name"],
                temperature=cached.get("temperature", 0.1),
                max_tokens=cached.get("max_tokens", 4096),
                fallback_provider=(
                    LLMProvider(cached["fallback_provider"])
                    if cached.get("fallback_provider")
                    else None
                ),
                fallback_model=cached.get("fallback_model"),
                rate_limit_rpm=cached.get("rate_limit_rpm", 60),
            )
            self._tenant_configs[cache_key] = config
            return config

        # TODO: Load from database if not in cache
        return None

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: LLMTaskType = LLMTaskType.VALIDATION,
        tenant_id: Optional[UUID] = None,
        json_mode: bool = False,
        cache_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ValidationLLMResult:
        """
        Execute an LLM completion with tenant-specific configuration.

        Args:
            prompt: The prompt to send
            system_prompt: Optional system prompt
            task_type: Type of task for configuration lookup
            tenant_id: Optional tenant ID for custom configuration
            json_mode: Whether to request JSON output
            cache_key: Optional cache key for response caching
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            ValidationLLMResult with response and metrics
        """
        import time
        start_time = time.perf_counter()

        # Check cache if key provided
        if cache_key:
            cached = await self.cache.get(f"llm:{cache_key}")
            if cached:
                logger.debug(f"LLM cache hit for {cache_key}")
                return ValidationLLMResult(
                    success=True,
                    content=cached.get("content", ""),
                    parsed_data=cached.get("parsed_data"),
                    confidence=cached.get("confidence", 0.8),
                    provider_used="cache",
                    model_used="cache",
                    latency_ms=0,
                )

        # Get tenant configuration if available
        config = None
        if tenant_id:
            config = await self.get_tenant_config(tenant_id, task_type)

        # Build request
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(LLMMessage(role=MessageRole.USER, content=prompt))

        request = LLMRequest(
            messages=messages,
            temperature=temperature or (config.temperature if config else 0.1),
            max_tokens=max_tokens or (config.max_tokens if config else 4096),
            json_mode=json_mode,
        )

        # Override model if tenant config specifies
        if config:
            model_prefix = self._get_model_prefix(config.provider)
            request.model_override = f"{model_prefix}{config.model_name}"

        try:
            # Execute request
            result = await self.llm_gateway.execute(request)

            if not result.success or not result.data:
                error_msg = result.error or "LLM request failed"
                return ValidationLLMResult(
                    success=False,
                    content="",
                    error=error_msg,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                )

            response = result.data
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Parse JSON if requested
            parsed_data = None
            if json_mode:
                try:
                    parsed_data = response.parse_json()
                except Exception as e:
                    logger.warning(f"Failed to parse JSON response: {e}")

            # Track usage
            usage = self._track_usage(
                task_type=task_type,
                provider=response.provider,
                model=response.model,
                usage_dict=response.usage,
                latency_ms=latency_ms,
                success=True,
            )

            result_obj = ValidationLLMResult(
                success=True,
                content=response.content,
                parsed_data=parsed_data,
                confidence=response.confidence or 0.8,
                provider_used=response.provider,
                model_used=response.model,
                latency_ms=latency_ms,
                usage=usage,
            )

            # Cache result if key provided
            if cache_key:
                await self.cache.set(
                    f"llm:{cache_key}",
                    {
                        "content": response.content,
                        "parsed_data": parsed_data,
                        "confidence": result_obj.confidence,
                    },
                    ttl=300,  # 5 minutes
                )

            return result_obj

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"LLM completion error: {e}")

            self._track_usage(
                task_type=task_type,
                provider=config.provider.value if config else "unknown",
                model=config.model_name if config else "unknown",
                usage_dict={},
                latency_ms=latency_ms,
                success=False,
            )

            return ValidationLLMResult(
                success=False,
                content="",
                error=str(e),
                latency_ms=latency_ms,
            )

    def _get_model_prefix(self, provider: LLMProvider) -> str:
        """Get model prefix for LiteLLM based on provider."""
        prefixes = {
            LLMProvider.AZURE: "azure/",
            LLMProvider.OPENAI: "",
            LLMProvider.ANTHROPIC: "",
            LLMProvider.OLLAMA: "ollama/",
            LLMProvider.VLLM: "openai/",  # vLLM uses OpenAI-compatible API
        }
        return prefixes.get(provider, "")

    def _track_usage(
        self,
        task_type: LLMTaskType,
        provider: str,
        model: str,
        usage_dict: dict,
        latency_ms: int,
        success: bool,
    ) -> LLMUsageMetrics:
        """Track LLM usage metrics."""
        prompt_tokens = usage_dict.get("prompt_tokens", 0)
        completion_tokens = usage_dict.get("completion_tokens", 0)
        total_tokens = usage_dict.get("total_tokens", prompt_tokens + completion_tokens)

        # Estimate cost
        estimated_cost = self._estimate_cost(model, prompt_tokens, completion_tokens)

        metrics = LLMUsageMetrics(
            task_type=task_type,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            success=success,
            estimated_cost_usd=estimated_cost,
        )

        self._usage_buffer.append(metrics)

        # Flush buffer periodically (every 100 entries)
        if len(self._usage_buffer) >= 100:
            asyncio.create_task(self._flush_usage_buffer())

        return metrics

    def _estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate cost in USD based on token counts."""
        # Find matching cost config
        cost_config = None
        model_lower = model.lower()

        for model_pattern, costs in COST_PER_1M_TOKENS.items():
            if model_pattern in model_lower:
                cost_config = costs
                break

        if not cost_config:
            return 0.0

        input_cost = (prompt_tokens / 1_000_000) * cost_config["input"]
        output_cost = (completion_tokens / 1_000_000) * cost_config["output"]

        return round(input_cost + output_cost, 6)

    async def _flush_usage_buffer(self) -> None:
        """Flush usage buffer to database."""
        if not self._usage_buffer:
            return

        buffer = self._usage_buffer.copy()
        self._usage_buffer.clear()

        # TODO: Insert into llm_usage_logs table
        logger.debug(f"Flushed {len(buffer)} LLM usage entries")

    async def get_usage_stats(
        self,
        tenant_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get aggregated usage statistics."""
        # TODO: Query from database
        return {
            "total_requests": len(self._usage_buffer),
            "total_tokens": sum(m.total_tokens for m in self._usage_buffer),
            "total_cost_usd": sum(m.estimated_cost_usd for m in self._usage_buffer),
            "avg_latency_ms": (
                sum(m.latency_ms for m in self._usage_buffer) / len(self._usage_buffer)
                if self._usage_buffer
                else 0
            ),
        }


# Singleton instance
_llm_validation_service: Optional[LLMValidationService] = None


def get_llm_validation_service() -> LLMValidationService:
    """Get or create the singleton LLM validation service."""
    global _llm_validation_service
    if _llm_validation_service is None:
        _llm_validation_service = LLMValidationService()
    return _llm_validation_service


async def create_llm_validation_service() -> LLMValidationService:
    """Create and initialize LLM validation service."""
    service = LLMValidationService()
    await service.initialize()
    return service
