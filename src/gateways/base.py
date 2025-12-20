"""
Base Gateway Abstract Class for Provider Abstraction Layer.

Implements the Strategy Pattern for swappable AI/ML providers with:
- Automatic fallback on failure
- Health monitoring
- Usage tracking
- Confidence thresholding
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Generic, Optional, TypeVar, Callable
import asyncio
import logging
import time
from functools import wraps

from src.core.enums import ProviderStatus

logger = logging.getLogger(__name__)

# Type variables for generic gateway pattern
TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")
TProvider = TypeVar("TProvider", bound=Enum)


class GatewayError(Exception):
    """Base exception for gateway errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


class ProviderUnavailableError(GatewayError):
    """Raised when a provider is not available."""

    pass


class ProviderTimeoutError(GatewayError):
    """Raised when a provider request times out."""

    pass


class ProviderRateLimitError(GatewayError):
    """Raised when a provider rate limit is exceeded."""

    pass


class ProviderAuthenticationError(GatewayError):
    """Raised when provider authentication fails."""

    pass


@dataclass
class GatewayConfig:
    """Configuration for a gateway instance."""

    primary_provider: str
    fallback_provider: Optional[str] = None
    fallback_on_error: bool = True
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    confidence_threshold: float = 0.85
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: float = 60.0
    health_check_interval_seconds: float = 30.0


@dataclass
class GatewayResult(Generic[TResponse]):
    """Result wrapper for gateway responses."""

    success: bool
    data: Optional[TResponse] = None
    error: Optional[str] = None
    provider_used: Optional[str] = None
    latency_ms: float = 0.0
    confidence: Optional[float] = None
    fallback_used: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_low_confidence(self) -> bool:
        """Check if result has low confidence."""
        if self.confidence is None:
            return False
        return self.confidence < 0.85


@dataclass
class ProviderHealth:
    """Health status for a provider."""

    status: ProviderStatus = ProviderStatus.HEALTHY
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    avg_latency_ms: float = 0.0
    request_count: int = 0
    error_count: int = 0
    circuit_open_until: Optional[datetime] = None

    @property
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.circuit_open_until is None:
            return False
        return datetime.now(timezone.utc) < self.circuit_open_until

    def record_success(self, latency_ms: float) -> None:
        """Record a successful request."""
        self.consecutive_failures = 0
        self.request_count += 1
        self.last_check = datetime.now(timezone.utc)
        self.circuit_open_until = None
        # Update rolling average latency
        if self.request_count == 1:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = (
                self.avg_latency_ms * 0.9 + latency_ms * 0.1
            )
        self.status = ProviderStatus.HEALTHY

    def record_failure(
        self, error: str, circuit_breaker_threshold: int, timeout_seconds: float
    ) -> None:
        """Record a failed request."""
        self.consecutive_failures += 1
        self.error_count += 1
        self.request_count += 1
        self.last_error = error
        self.last_check = datetime.now(timezone.utc)

        if self.consecutive_failures >= circuit_breaker_threshold:
            self.circuit_open_until = datetime.now(timezone.utc) + timedelta(
                seconds=timeout_seconds
            )
            self.status = ProviderStatus.UNHEALTHY
        elif self.consecutive_failures >= circuit_breaker_threshold // 2:
            self.status = ProviderStatus.DEGRADED


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for retry logic with exponential backoff."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


class BaseGateway(ABC, Generic[TRequest, TResponse, TProvider]):
    """
    Abstract base class for all provider gateways.

    Implements:
    - Primary/fallback provider pattern
    - Automatic failover on error
    - Circuit breaker pattern
    - Health monitoring
    - Usage tracking
    - Retry with exponential backoff
    """

    def __init__(self, config: GatewayConfig):
        self.config = config
        self._health: dict[str, ProviderHealth] = {}
        self._initialized = False
        self._lock = asyncio.Lock()

    @property
    @abstractmethod
    def gateway_name(self) -> str:
        """Name of this gateway for logging."""
        pass

    @abstractmethod
    async def _initialize_provider(self, provider: TProvider) -> None:
        """Initialize a specific provider."""
        pass

    @abstractmethod
    async def _execute_request(
        self, request: TRequest, provider: TProvider
    ) -> TResponse:
        """Execute a request using the specified provider."""
        pass

    @abstractmethod
    async def _health_check(self, provider: TProvider) -> bool:
        """Perform health check for a provider."""
        pass

    @abstractmethod
    def _parse_provider(self, provider_str: str) -> TProvider:
        """Parse provider string to enum."""
        pass

    def _get_health(self, provider: str) -> ProviderHealth:
        """Get or create health status for a provider."""
        if provider not in self._health:
            self._health[provider] = ProviderHealth()
        return self._health[provider]

    async def initialize(self) -> None:
        """Initialize the gateway and all configured providers."""
        async with self._lock:
            if self._initialized:
                return

            logger.info(f"Initializing {self.gateway_name} gateway...")

            # Initialize primary provider
            primary = self._parse_provider(self.config.primary_provider)
            try:
                await self._initialize_provider(primary)
                self._get_health(self.config.primary_provider).status = (
                    ProviderStatus.HEALTHY
                )
                logger.info(
                    f"Primary provider {self.config.primary_provider} initialized"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize primary provider "
                    f"{self.config.primary_provider}: {e}"
                )
                self._get_health(self.config.primary_provider).status = (
                    ProviderStatus.UNHEALTHY
                )

            # Initialize fallback provider if configured
            if self.config.fallback_provider:
                fallback = self._parse_provider(self.config.fallback_provider)
                try:
                    await self._initialize_provider(fallback)
                    self._get_health(self.config.fallback_provider).status = (
                        ProviderStatus.HEALTHY
                    )
                    logger.info(
                        f"Fallback provider {self.config.fallback_provider} initialized"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize fallback provider "
                        f"{self.config.fallback_provider}: {e}"
                    )
                    self._get_health(self.config.fallback_provider).status = (
                        ProviderStatus.UNHEALTHY
                    )

            self._initialized = True
            logger.info(f"{self.gateway_name} gateway initialized")

    async def execute(self, request: TRequest) -> GatewayResult[TResponse]:
        """
        Execute a request with automatic failover.

        Attempts primary provider first, falls back on failure if configured.
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.perf_counter()
        result = GatewayResult[TResponse](success=False)

        # Try primary provider
        primary_health = self._get_health(self.config.primary_provider)
        if not primary_health.is_circuit_open:
            try:
                primary = self._parse_provider(self.config.primary_provider)
                response = await asyncio.wait_for(
                    self._execute_with_retry(request, primary),
                    timeout=self.config.timeout_seconds,
                )
                latency = (time.perf_counter() - start_time) * 1000

                primary_health.record_success(latency)

                result.success = True
                result.data = response
                result.provider_used = self.config.primary_provider
                result.latency_ms = latency
                result.confidence = getattr(response, "confidence", None)

                logger.debug(
                    f"{self.gateway_name}: Primary provider "
                    f"{self.config.primary_provider} succeeded in {latency:.1f}ms"
                )
                return result

            except asyncio.TimeoutError:
                error_msg = f"Timeout after {self.config.timeout_seconds}s"
                primary_health.record_failure(
                    error_msg,
                    self.config.circuit_breaker_threshold,
                    self.config.circuit_breaker_timeout_seconds,
                )
                result.error = error_msg
                logger.warning(
                    f"{self.gateway_name}: Primary provider "
                    f"{self.config.primary_provider} timed out"
                )

            except Exception as e:
                error_msg = str(e)
                primary_health.record_failure(
                    error_msg,
                    self.config.circuit_breaker_threshold,
                    self.config.circuit_breaker_timeout_seconds,
                )
                result.error = error_msg
                logger.warning(
                    f"{self.gateway_name}: Primary provider "
                    f"{self.config.primary_provider} failed: {e}"
                )
        else:
            logger.info(
                f"{self.gateway_name}: Primary provider circuit breaker open, "
                "skipping to fallback"
            )
            result.error = "Circuit breaker open"

        # Try fallback provider if configured and allowed
        if (
            self.config.fallback_provider
            and self.config.fallback_on_error
        ):
            fallback_health = self._get_health(self.config.fallback_provider)
            if not fallback_health.is_circuit_open:
                try:
                    fallback = self._parse_provider(self.config.fallback_provider)
                    response = await asyncio.wait_for(
                        self._execute_with_retry(request, fallback),
                        timeout=self.config.timeout_seconds,
                    )
                    latency = (time.perf_counter() - start_time) * 1000

                    fallback_health.record_success(latency)

                    result.success = True
                    result.data = response
                    result.provider_used = self.config.fallback_provider
                    result.latency_ms = latency
                    result.fallback_used = True
                    result.confidence = getattr(response, "confidence", None)

                    logger.info(
                        f"{self.gateway_name}: Fallback provider "
                        f"{self.config.fallback_provider} succeeded in {latency:.1f}ms"
                    )
                    return result

                except asyncio.TimeoutError:
                    error_msg = f"Fallback timeout after {self.config.timeout_seconds}s"
                    fallback_health.record_failure(
                        error_msg,
                        self.config.circuit_breaker_threshold,
                        self.config.circuit_breaker_timeout_seconds,
                    )
                    result.error = f"Primary and fallback failed: {result.error}; {error_msg}"

                except Exception as e:
                    error_msg = str(e)
                    fallback_health.record_failure(
                        error_msg,
                        self.config.circuit_breaker_threshold,
                        self.config.circuit_breaker_timeout_seconds,
                    )
                    result.error = f"Primary and fallback failed: {result.error}; {error_msg}"

        result.latency_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def _execute_with_retry(
        self, request: TRequest, provider: TProvider
    ) -> TResponse:
        """Execute request with retry logic."""
        last_exception = None
        delay = self.config.retry_delay_seconds

        for attempt in range(self.config.retry_attempts):
            try:
                return await self._execute_request(request, provider)
            except (ProviderRateLimitError,) as e:
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    logger.warning(
                        f"Rate limit hit, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.config.retry_attempts})"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
            except Exception as e:
                raise e

        raise last_exception or GatewayError("All retry attempts failed")

    async def check_health(self) -> dict[str, ProviderHealth]:
        """Check health of all configured providers."""
        if not self._initialized:
            await self.initialize()

        providers = [self.config.primary_provider]
        if self.config.fallback_provider:
            providers.append(self.config.fallback_provider)

        for provider_str in providers:
            provider = self._parse_provider(provider_str)
            health = self._get_health(provider_str)

            try:
                is_healthy = await self._health_check(provider)
                if is_healthy:
                    health.status = ProviderStatus.HEALTHY
                else:
                    health.status = ProviderStatus.DEGRADED
            except Exception as e:
                health.status = ProviderStatus.UNHEALTHY
                health.last_error = str(e)

            health.last_check = datetime.now(timezone.utc)

        return self._health.copy()

    def get_provider_status(self, provider: str) -> ProviderHealth:
        """Get current health status for a provider."""
        return self._get_health(provider)

    def get_all_status(self) -> dict[str, ProviderHealth]:
        """Get health status for all providers."""
        return self._health.copy()

    async def close(self) -> None:
        """Clean up gateway resources."""
        self._initialized = False
        logger.info(f"{self.gateway_name} gateway closed")
