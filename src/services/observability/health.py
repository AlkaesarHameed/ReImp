"""
Health Check Service.
Source: Design Document Section 5.3 - Monitoring & Observability
Verified: 2025-12-18

Provides health check endpoints for service monitoring.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status of a component."""

    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: Optional[str] = None
    response_time_ms: float = 0.0
    last_check: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)

    # Thresholds
    warning_threshold_ms: float = 1000.0
    critical_threshold_ms: float = 5000.0


class HealthCheck(BaseModel):
    """Overall health check result."""

    status: HealthStatus = HealthStatus.UNKNOWN
    version: str = "1.0.0"
    service_name: str = "claims-processor"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Component health
    components: dict[str, ComponentHealth] = Field(default_factory=dict)

    # Metrics
    uptime_seconds: float = 0.0
    total_checks: int = 0
    failed_checks: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "service": self.service_name,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "components": {
                name: {
                    "status": comp.status.value,
                    "message": comp.message,
                    "response_time_ms": comp.response_time_ms,
                    "last_check": comp.last_check.isoformat(),
                }
                for name, comp in self.components.items()
            },
        }


class HealthCheckService:
    """Health check service for monitoring."""

    def __init__(
        self,
        service_name: str = "claims-processor",
        version: str = "1.0.0",
    ):
        """Initialize health check service.

        Args:
            service_name: Name of the service
            version: Service version
        """
        self._service_name = service_name
        self._version = version
        self._start_time = time.perf_counter()

        # Registered health checks
        self._checks: dict[str, Callable[[], ComponentHealth]] = {}
        self._async_checks: dict[str, Callable[[], ComponentHealth]] = {}

        # Component status cache
        self._component_status: dict[str, ComponentHealth] = {}

        # Statistics
        self._total_checks = 0
        self._failed_checks = 0

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return time.perf_counter() - self._start_time

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], ComponentHealth],
        is_async: bool = False,
    ) -> None:
        """Register a health check.

        Args:
            name: Component name
            check_fn: Health check function
            is_async: Whether the check is async
        """
        if is_async:
            self._async_checks[name] = check_fn
        else:
            self._checks[name] = check_fn

    def unregister_check(self, name: str) -> None:
        """Unregister a health check.

        Args:
            name: Component name
        """
        self._checks.pop(name, None)
        self._async_checks.pop(name, None)
        self._component_status.pop(name, None)

    def _run_check(self, name: str, check_fn: Callable) -> ComponentHealth:
        """Run a single health check.

        Args:
            name: Component name
            check_fn: Check function

        Returns:
            Component health status
        """
        start = time.perf_counter()

        try:
            result = check_fn()
            result.response_time_ms = (time.perf_counter() - start) * 1000
            result.last_check = datetime.utcnow()

            # Update status based on response time
            if result.status == HealthStatus.HEALTHY:
                if result.response_time_ms > result.critical_threshold_ms:
                    result.status = HealthStatus.UNHEALTHY
                    result.message = f"Response time {result.response_time_ms:.0f}ms exceeds critical threshold"
                elif result.response_time_ms > result.warning_threshold_ms:
                    result.status = HealthStatus.DEGRADED
                    result.message = f"Response time {result.response_time_ms:.0f}ms exceeds warning threshold"

            return result

        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                response_time_ms=(time.perf_counter() - start) * 1000,
            )

    async def _run_async_check(self, name: str, check_fn: Callable) -> ComponentHealth:
        """Run an async health check.

        Args:
            name: Component name
            check_fn: Async check function

        Returns:
            Component health status
        """
        start = time.perf_counter()

        try:
            result = await check_fn()
            result.response_time_ms = (time.perf_counter() - start) * 1000
            result.last_check = datetime.utcnow()

            return result

        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                response_time_ms=(time.perf_counter() - start) * 1000,
            )

    def check(self) -> HealthCheck:
        """Run all health checks synchronously.

        Returns:
            Overall health check result
        """
        self._total_checks += 1
        components: dict[str, ComponentHealth] = {}

        # Run sync checks
        for name, check_fn in self._checks.items():
            result = self._run_check(name, check_fn)
            components[name] = result
            self._component_status[name] = result

            if result.status == HealthStatus.UNHEALTHY:
                self._failed_checks += 1

        # Determine overall status
        overall_status = self._determine_overall_status(components)

        return HealthCheck(
            status=overall_status,
            version=self._version,
            service_name=self._service_name,
            components=components,
            uptime_seconds=self.uptime_seconds,
            total_checks=self._total_checks,
            failed_checks=self._failed_checks,
        )

    async def check_async(self) -> HealthCheck:
        """Run all health checks asynchronously.

        Returns:
            Overall health check result
        """
        self._total_checks += 1
        components: dict[str, ComponentHealth] = {}

        # Run sync checks
        for name, check_fn in self._checks.items():
            result = self._run_check(name, check_fn)
            components[name] = result
            self._component_status[name] = result

        # Run async checks concurrently
        if self._async_checks:
            async_results = await asyncio.gather(
                *[
                    self._run_async_check(name, check_fn)
                    for name, check_fn in self._async_checks.items()
                ],
                return_exceptions=True,
            )

            for name, result in zip(self._async_checks.keys(), async_results):
                if isinstance(result, Exception):
                    components[name] = ComponentHealth(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(result),
                    )
                else:
                    components[name] = result
                    self._component_status[name] = result

        # Count failures
        failed = sum(
            1 for c in components.values() if c.status == HealthStatus.UNHEALTHY
        )
        if failed > 0:
            self._failed_checks += 1

        # Determine overall status
        overall_status = self._determine_overall_status(components)

        return HealthCheck(
            status=overall_status,
            version=self._version,
            service_name=self._service_name,
            components=components,
            uptime_seconds=self.uptime_seconds,
            total_checks=self._total_checks,
            failed_checks=self._failed_checks,
        )

    def _determine_overall_status(
        self, components: dict[str, ComponentHealth]
    ) -> HealthStatus:
        """Determine overall health status from components.

        Args:
            components: Component health statuses

        Returns:
            Overall status
        """
        if not components:
            return HealthStatus.HEALTHY

        statuses = [c.status for c in components.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def get_component_status(self, name: str) -> ComponentHealth | None:
        """Get cached status for a component.

        Args:
            name: Component name

        Returns:
            Component health or None
        """
        return self._component_status.get(name)

    def liveness(self) -> dict:
        """Kubernetes liveness probe endpoint.

        Returns:
            Simple status response
        """
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def readiness(self) -> dict:
        """Kubernetes readiness probe endpoint.

        Returns:
            Readiness status with component checks
        """
        health = self.check()

        return {
            "status": "ready" if health.status == HealthStatus.HEALTHY else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                name: comp.status.value for name, comp in health.components.items()
            },
        }

    def startup(self) -> dict:
        """Kubernetes startup probe endpoint.

        Returns:
            Startup status
        """
        return {
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": self.uptime_seconds,
        }


# =============================================================================
# Standard Health Check Functions
# =============================================================================


def check_database(
    connection_fn: Callable[[], bool],
    name: str = "database",
) -> ComponentHealth:
    """Create database health check.

    Args:
        connection_fn: Function that returns True if connected
        name: Component name

    Returns:
        Health check result
    """
    try:
        if connection_fn():
            return ComponentHealth(
                name=name,
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
            )
        else:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Database connection failed",
            )
    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Database error: {str(e)}",
        )


def check_memory(
    threshold_percent: float = 90.0,
    name: str = "memory",
) -> ComponentHealth:
    """Create memory health check.

    Args:
        threshold_percent: Memory usage threshold
        name: Component name

    Returns:
        Health check result
    """
    try:
        import psutil

        memory = psutil.virtual_memory()
        usage_percent = memory.percent

        status = HealthStatus.HEALTHY
        if usage_percent > threshold_percent:
            status = HealthStatus.UNHEALTHY
        elif usage_percent > threshold_percent * 0.8:
            status = HealthStatus.DEGRADED

        return ComponentHealth(
            name=name,
            status=status,
            message=f"Memory usage: {usage_percent:.1f}%",
            details={
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": usage_percent,
            },
        )
    except ImportError:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            message="psutil not available",
        )
    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Memory check error: {str(e)}",
        )


def check_disk(
    path: str = "/",
    threshold_percent: float = 90.0,
    name: str = "disk",
) -> ComponentHealth:
    """Create disk health check.

    Args:
        path: Disk path to check
        threshold_percent: Disk usage threshold
        name: Component name

    Returns:
        Health check result
    """
    try:
        import psutil

        disk = psutil.disk_usage(path)
        usage_percent = disk.percent

        status = HealthStatus.HEALTHY
        if usage_percent > threshold_percent:
            status = HealthStatus.UNHEALTHY
        elif usage_percent > threshold_percent * 0.8:
            status = HealthStatus.DEGRADED

        return ComponentHealth(
            name=name,
            status=status,
            message=f"Disk usage: {usage_percent:.1f}%",
            details={
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": usage_percent,
            },
        )
    except ImportError:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            message="psutil not available",
        )
    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Disk check error: {str(e)}",
        )


# =============================================================================
# Factory Functions
# =============================================================================


_health_service: HealthCheckService | None = None


def get_health_service(service_name: str = "claims-processor") -> HealthCheckService:
    """Get singleton health check service."""
    global _health_service
    if _health_service is None:
        _health_service = HealthCheckService(service_name=service_name)
    return _health_service


def create_health_service(
    service_name: str = "claims-processor",
    version: str = "1.0.0",
) -> HealthCheckService:
    """Create new health check service."""
    return HealthCheckService(service_name=service_name, version=version)
