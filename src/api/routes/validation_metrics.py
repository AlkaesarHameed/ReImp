"""
Validation Metrics API Routes.

Source: Design Document 04_validation_engine_comprehensive_design.md
Phase 5.4: Performance Monitoring API

Provides endpoints for:
- Real-time validation performance metrics
- Rule execution statistics
- Cache effectiveness metrics
- SLA compliance reporting
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.services.validation.performance import (
    get_validation_cache,
    get_validation_performance_monitor,
    get_batch_processor,
    ValidationPerformanceConfig,
)
from src.services.performance.monitor import get_performance_monitor

router = APIRouter(prefix="/validation/metrics", tags=["validation-metrics"])


# =============================================================================
# Response Models
# =============================================================================


class TimerStatsResponse(BaseModel):
    """Timer statistics response."""

    name: str
    count: int
    total_ms: float
    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float


class ValidationMetricsResponse(BaseModel):
    """Validation performance metrics response."""

    validations: dict
    timing: dict
    sla: dict
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuleMetricsResponse(BaseModel):
    """Per-rule performance metrics response."""

    rules: dict[str, TimerStatsResponse]
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CacheMetricsResponse(BaseModel):
    """Cache performance metrics response."""

    caches: dict
    overall_hit_rate: float
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PerformanceSummaryResponse(BaseModel):
    """Complete performance summary response."""

    validation: ValidationMetricsResponse
    rules: dict[str, TimerStatsResponse]
    cache: CacheMetricsResponse
    system: dict
    alerts: list[dict]
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HealthCheckResponse(BaseModel):
    """Performance health check response."""

    status: str  # healthy, degraded, unhealthy
    checks: dict[str, bool]
    issues: list[str]
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("", response_model=PerformanceSummaryResponse)
async def get_performance_summary():
    """
    Get complete validation performance summary.

    Returns comprehensive metrics including:
    - Validation statistics (total, pass/fail rates)
    - Timing metrics (avg, percentiles)
    - Per-rule performance
    - Cache effectiveness
    - System resource usage
    - Active alerts
    """
    monitor = get_validation_performance_monitor()
    cache = get_validation_cache()
    system_monitor = get_performance_monitor()

    # Get validation metrics
    validation_metrics = monitor.get_validation_metrics()

    # Get rule metrics
    rule_metrics_raw = monitor.get_rule_metrics()
    rule_metrics = {
        name: TimerStatsResponse(
            name=name,
            count=stats.count,
            total_ms=stats.total_ms,
            min_ms=stats.min_ms if stats.count > 0 else 0,
            max_ms=stats.max_ms if stats.count > 0 else 0,
            avg_ms=stats.avg_ms,
            p50_ms=stats.p50_ms,
            p90_ms=stats.p90_ms,
            p95_ms=stats.p95_ms,
            p99_ms=stats.p99_ms,
        )
        for name, stats in rule_metrics_raw.items()
    }

    # Get cache metrics
    cache_metrics = monitor.get_cache_metrics()
    cache_stats = cache.get_stats()

    total_hits = sum(c.get("hits", 0) for c in cache_metrics.values())
    total_misses = sum(c.get("misses", 0) for c in cache_metrics.values())
    overall_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0

    # Get system metrics
    system_metrics = system_monitor.get_metrics()

    # Check for alerts
    alerts = []
    config = ValidationPerformanceConfig()

    if overall_hit_rate < config.cache_hit_rate_alert_threshold:
        alerts.append({
            "type": "low_cache_hit_rate",
            "severity": "warning",
            "message": f"Cache hit rate ({overall_hit_rate:.1f}%) below threshold ({config.cache_hit_rate_alert_threshold}%)",
        })

    if validation_metrics["timing"]["p95_ms"] > config.p95_latency_alert_threshold_ms:
        alerts.append({
            "type": "high_latency",
            "severity": "warning",
            "message": f"P95 latency ({validation_metrics['timing']['p95_ms']:.0f}ms) exceeds threshold ({config.p95_latency_alert_threshold_ms}ms)",
        })

    if validation_metrics["validations"]["error_rate"] > config.error_rate_alert_threshold:
        alerts.append({
            "type": "high_error_rate",
            "severity": "error",
            "message": f"Error rate ({validation_metrics['validations']['error_rate']:.1f}%) exceeds threshold ({config.error_rate_alert_threshold}%)",
        })

    return PerformanceSummaryResponse(
        validation=ValidationMetricsResponse(
            validations=validation_metrics["validations"],
            timing=validation_metrics["timing"],
            sla=validation_metrics["sla"],
        ),
        rules=rule_metrics,
        cache=CacheMetricsResponse(
            caches=cache_metrics,
            overall_hit_rate=overall_hit_rate,
        ),
        system={
            "total_requests": system_metrics.total_requests,
            "requests_per_second": system_metrics.requests_per_second,
            "memory_usage_mb": system_metrics.memory_usage_mb,
            "error_rate": system_metrics.error_rate,
        },
        alerts=alerts,
    )


@router.get("/validation", response_model=ValidationMetricsResponse)
async def get_validation_metrics():
    """
    Get validation-specific performance metrics.

    Returns:
    - Total validations count
    - Pass/fail/error breakdown
    - Timing statistics (avg, percentiles)
    - SLA compliance metrics
    """
    monitor = get_validation_performance_monitor()
    return ValidationMetricsResponse(**monitor.get_validation_metrics())


@router.get("/rules", response_model=RuleMetricsResponse)
async def get_rule_metrics():
    """
    Get per-rule execution metrics.

    Returns timing statistics for each validation rule:
    - Rule 1: Insured Data Extraction
    - Rule 2: Code Extraction
    - Rule 3: PDF Forensics
    - Rule 4: ICD-CPT Crosswalk
    - Rule 5: Clinical Necessity
    - Rule 6: ICD×ICD Conflicts
    - Rules 7-8: Demographics
    - Rule 9: Documentation Review
    """
    monitor = get_validation_performance_monitor()
    rule_metrics_raw = monitor.get_rule_metrics()

    rule_metrics = {
        name: TimerStatsResponse(
            name=name,
            count=stats.count,
            total_ms=stats.total_ms,
            min_ms=stats.min_ms if stats.count > 0 else 0,
            max_ms=stats.max_ms if stats.count > 0 else 0,
            avg_ms=stats.avg_ms,
            p50_ms=stats.p50_ms,
            p90_ms=stats.p90_ms,
            p95_ms=stats.p95_ms,
            p99_ms=stats.p99_ms,
        )
        for name, stats in rule_metrics_raw.items()
    }

    return RuleMetricsResponse(rules=rule_metrics)


@router.get("/cache", response_model=CacheMetricsResponse)
async def get_cache_metrics():
    """
    Get cache performance metrics.

    Returns hit/miss statistics for each cache type:
    - ICD code cache
    - CPT code cache
    - Crosswalk cache
    - LLM response cache
    """
    monitor = get_validation_performance_monitor()
    cache = get_validation_cache()

    cache_metrics = monitor.get_cache_metrics()
    cache_stats = cache.get_stats()

    total_hits = sum(c.get("hits", 0) for c in cache_metrics.values())
    total_misses = sum(c.get("misses", 0) for c in cache_metrics.values())
    overall_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0

    return CacheMetricsResponse(
        caches={
            **cache_metrics,
            "detailed": cache_stats,
        },
        overall_hit_rate=overall_hit_rate,
    )


@router.get("/health", response_model=HealthCheckResponse)
async def check_performance_health():
    """
    Perform performance health check.

    Checks:
    - Validation latency within SLA
    - Cache hit rate acceptable
    - Error rate within limits
    - No critical alerts
    """
    monitor = get_validation_performance_monitor()
    config = ValidationPerformanceConfig()

    validation_metrics = monitor.get_validation_metrics()
    cache_metrics = monitor.get_cache_metrics()

    total_hits = sum(c.get("hits", 0) for c in cache_metrics.values())
    total_misses = sum(c.get("misses", 0) for c in cache_metrics.values())
    cache_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 100

    # Perform checks
    checks = {
        "latency_ok": validation_metrics["timing"]["p95_ms"] <= config.p95_latency_alert_threshold_ms,
        "cache_ok": cache_hit_rate >= config.cache_hit_rate_alert_threshold,
        "error_rate_ok": validation_metrics["validations"]["error_rate"] <= config.error_rate_alert_threshold,
        "sla_compliance_ok": validation_metrics["sla"]["compliance_rate"] >= 95.0,
    }

    issues = []
    if not checks["latency_ok"]:
        issues.append(f"P95 latency ({validation_metrics['timing']['p95_ms']:.0f}ms) exceeds threshold")
    if not checks["cache_ok"]:
        issues.append(f"Cache hit rate ({cache_hit_rate:.1f}%) below threshold")
    if not checks["error_rate_ok"]:
        issues.append(f"Error rate ({validation_metrics['validations']['error_rate']:.1f}%) too high")
    if not checks["sla_compliance_ok"]:
        issues.append(f"SLA compliance ({validation_metrics['sla']['compliance_rate']:.1f}%) below 95%")

    # Determine overall status
    if all(checks.values()):
        status = "healthy"
    elif checks["latency_ok"] and checks["error_rate_ok"]:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthCheckResponse(
        status=status,
        checks=checks,
        issues=issues,
    )


@router.post("/reset")
async def reset_metrics():
    """
    Reset all validation performance metrics.

    This clears:
    - Validation counters
    - Timing history
    - SLA violation counts
    """
    monitor = get_validation_performance_monitor()
    monitor.reset()

    return {"status": "ok", "message": "Metrics reset successfully"}


@router.post("/cache/clear")
async def clear_cache(
    cache_type: Optional[str] = Query(
        None,
        description="Cache type to clear: 'code', 'crosswalk', 'llm', or 'all' (default)",
    ),
):
    """
    Clear validation caches.

    Clearing caches will temporarily reduce performance until
    the cache is repopulated.
    """
    cache = get_validation_cache()

    if cache_type == "code":
        await cache.clear_code_cache()
        cleared = "code cache"
    elif cache_type == "crosswalk":
        await cache.clear_crosswalk_cache()
        cleared = "crosswalk cache"
    elif cache_type == "llm":
        await cache._llm_cache.clear()
        cleared = "LLM cache"
    else:
        await cache.clear_all()
        cleared = "all caches"

    return {"status": "ok", "message": f"Cleared {cleared}"}


@router.get("/prometheus")
async def get_prometheus_metrics():
    """
    Export metrics in Prometheus format.

    Returns metrics in Prometheus text exposition format
    for scraping by Prometheus server.
    """
    system_monitor = get_performance_monitor()
    validation_monitor = get_validation_performance_monitor()

    # Get base prometheus metrics
    prometheus_output = system_monitor.export_prometheus()

    # Add validation-specific metrics
    validation_metrics = validation_monitor.get_validation_metrics()

    lines = [
        prometheus_output,
        "",
        "# HELP validation_total Total validations performed",
        "# TYPE validation_total counter",
        f"validation_total {validation_metrics['validations']['total']}",
        "",
        "# HELP validation_passed Validations that passed",
        "# TYPE validation_passed counter",
        f"validation_passed {validation_metrics['validations']['passed']}",
        "",
        "# HELP validation_failed Validations that failed",
        "# TYPE validation_failed counter",
        f"validation_failed {validation_metrics['validations']['failed']}",
        "",
        "# HELP validation_latency_ms Validation latency in milliseconds",
        "# TYPE validation_latency_ms summary",
        f'validation_latency_ms{{quantile="0.5"}} {validation_metrics["timing"]["p50_ms"]}',
        f'validation_latency_ms{{quantile="0.95"}} {validation_metrics["timing"]["p95_ms"]}',
        f'validation_latency_ms{{quantile="0.99"}} {validation_metrics["timing"]["p99_ms"]}',
        "",
        "# HELP sla_compliance_rate SLA compliance percentage",
        "# TYPE sla_compliance_rate gauge",
        f"sla_compliance_rate {validation_metrics['sla']['compliance_rate']}",
    ]

    return "\n".join(lines)
