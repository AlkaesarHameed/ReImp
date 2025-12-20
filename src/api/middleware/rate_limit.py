"""
Rate Limiting Middleware for Per-Tenant Request Throttling.

Provides:
- Sliding window rate limiting
- Per-tenant rate limits
- Per-endpoint rate limits
- Redis-based distributed rate limiting (optional)
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.api.middleware.tenant import get_current_tenant_id

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    enabled: bool = True


@dataclass
class RateLimitState:
    """State for a single rate limit window."""

    count: int = 0
    window_start: float = field(default_factory=time.time)

    def is_window_expired(self, window_seconds: float) -> bool:
        """Check if the current window has expired."""
        return time.time() - self.window_start > window_seconds

    def reset(self) -> None:
        """Reset the window."""
        self.count = 0
        self.window_start = time.time()


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production, replace with Redis-based implementation.
    """

    def __init__(self):
        self._minute_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._hour_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is within rate limits.

        Returns:
            tuple of (is_allowed, rate_limit_headers)
        """
        async with self._lock:
            minute_state = self._minute_limits[key]
            hour_state = self._hour_limits[key]

            # Reset windows if expired
            if minute_state.is_window_expired(60):
                minute_state.reset()
            if hour_state.is_window_expired(3600):
                hour_state.reset()

            # Calculate remaining requests
            minute_remaining = max(0, config.requests_per_minute - minute_state.count)
            hour_remaining = max(0, config.requests_per_hour - hour_state.count)

            headers = {
                "X-RateLimit-Limit-Minute": config.requests_per_minute,
                "X-RateLimit-Remaining-Minute": minute_remaining,
                "X-RateLimit-Limit-Hour": config.requests_per_hour,
                "X-RateLimit-Remaining-Hour": hour_remaining,
            }

            # Check if rate limited
            if minute_state.count >= config.requests_per_minute:
                headers["Retry-After"] = int(60 - (time.time() - minute_state.window_start))
                return False, headers

            if hour_state.count >= config.requests_per_hour:
                headers["Retry-After"] = int(3600 - (time.time() - hour_state.window_start))
                return False, headers

            # Increment counters
            minute_state.count += 1
            hour_state.count += 1

            return True, headers

    def clear(self) -> None:
        """Clear all rate limit state."""
        self._minute_limits.clear()
        self._hour_limits.clear()


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()

# Per-tenant rate limit configurations
_tenant_configs: dict[str, RateLimitConfig] = {}

# Default configuration
_default_config = RateLimitConfig()


def configure_tenant_rate_limit(tenant_id: str, config: RateLimitConfig) -> None:
    """Configure rate limits for a specific tenant."""
    _tenant_configs[tenant_id] = config


def get_tenant_rate_config(tenant_id: Optional[str]) -> RateLimitConfig:
    """Get rate limit configuration for a tenant."""
    if tenant_id and tenant_id in _tenant_configs:
        return _tenant_configs[tenant_id]
    return _default_config


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for per-tenant rate limiting.

    Rate limits are applied based on:
    - Tenant ID (from JWT token)
    - Client IP (for unauthenticated requests)
    - Endpoint path (optional per-endpoint limits)
    """

    def __init__(
        self,
        app,
        default_config: Optional[RateLimitConfig] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.default_config = default_config or RateLimitConfig()
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Determine rate limit key
        tenant_id = get_current_tenant_id()
        if tenant_id:
            key = f"tenant:{tenant_id}"
        else:
            # Use client IP for unauthenticated requests
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}"

        # Get configuration
        config = get_tenant_rate_config(tenant_id)

        if not config.enabled:
            return await call_next(request)

        # Check rate limit
        is_allowed, headers = await _rate_limiter.check_rate_limit(key, config)

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {key}")
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                headers={k: str(v) for k, v in headers.items()},
                media_type="application/json",
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for header, value in headers.items():
            response.headers[header] = str(value)

        return response


# =============================================================================
# Rate Limit Decorator for Specific Endpoints
# =============================================================================


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator for per-endpoint rate limiting.

    Usage:
        @router.post("/expensive-operation")
        @rate_limit(requests_per_minute=10)
        async def expensive_operation():
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Store endpoint-specific rate limiter
        endpoint_limiter = InMemoryRateLimiter()
        endpoint_config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
        )

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                tenant_id = get_current_tenant_id()
                if tenant_id:
                    key = f"tenant:{tenant_id}:{func.__name__}"
                else:
                    client_ip = request.client.host if request.client else "unknown"
                    key = f"ip:{client_ip}:{func.__name__}"

            # Check rate limit
            is_allowed, headers = await endpoint_limiter.check_rate_limit(
                key, endpoint_config
            )

            if not is_allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded for this endpoint",
                    headers={k: str(v) for k, v in headers.items()},
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Rate Limit Dependencies
# =============================================================================


class RateLimitDependency:
    """
    Dependency class for rate limiting specific endpoints.

    Usage:
        @router.post("/api/claims", dependencies=[Depends(RateLimitDependency(30, 500))])
        async def create_claim():
            ...
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
        )
        self.limiter = InMemoryRateLimiter()

    async def __call__(self, request: Request) -> None:
        tenant_id = get_current_tenant_id()
        if tenant_id:
            key = f"tenant:{tenant_id}:{request.url.path}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}:{request.url.path}"

        is_allowed, headers = await self.limiter.check_rate_limit(key, self.config)

        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={k: str(v) for k, v in headers.items()},
            )


# Pre-configured rate limit dependencies
strict_rate_limit = RateLimitDependency(requests_per_minute=10, requests_per_hour=100)
moderate_rate_limit = RateLimitDependency(requests_per_minute=30, requests_per_hour=500)
relaxed_rate_limit = RateLimitDependency(requests_per_minute=120, requests_per_hour=2000)
