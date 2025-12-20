"""
Performance Monitoring Service.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides performance metrics collection and monitoring.
"""

import asyncio
import time
from collections import deque
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class MetricUnit(str, Enum):
    """Metric units."""

    COUNT = "count"
    MILLISECONDS = "ms"
    SECONDS = "s"
    BYTES = "bytes"
    PERCENT = "percent"
    REQUESTS = "requests"


class Metric(BaseModel):
    """Single metric entry."""

    name: str
    metric_type: MetricType
    value: float
    unit: MetricUnit = MetricUnit.COUNT
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: dict[str, str] = Field(default_factory=dict)


class HistogramBucket(BaseModel):
    """Histogram bucket for distribution analysis."""

    le: float  # Less than or equal to
    count: int = 0


class TimerStats(BaseModel):
    """Timer statistics."""

    name: str
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics."""

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    requests_per_second: float = 0.0

    # Resource metrics
    active_connections: int = 0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0

    # Error metrics
    error_rate: float = 0.0
    timeout_rate: float = 0.0

    # Custom timers
    timers: dict[str, TimerStats] = Field(default_factory=dict)

    # Timestamp
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class PerformanceMonitor:
    """Performance monitoring service."""

    def __init__(self, history_size: int = 10000):
        """Initialize PerformanceMonitor."""
        self._history_size = history_size

        # Counters
        self._counters: dict[str, int] = {}

        # Gauges
        self._gauges: dict[str, float] = {}

        # Timers (name -> list of durations in ms)
        self._timers: dict[str, deque[float]] = {}

        # Histograms
        self._histograms: dict[str, list[float]] = {}

        # Request tracking
        self._request_times: deque[float] = deque(maxlen=history_size)
        self._request_errors: int = 0
        self._request_timeouts: int = 0
        self._request_count: int = 0
        self._start_time = time.perf_counter()

        # Active spans for tracing
        self._active_spans: dict[str, float] = {}

        # Callbacks for alerts
        self._alert_callbacks: list[Callable[[str, float], None]] = []
        self._alert_thresholds: dict[str, float] = {}

    # =========================================================================
    # Counter Operations
    # =========================================================================

    def increment(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, tags)
        self._counters[key] = self._counters.get(key, 0) + value

    def decrement(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        """Decrement a counter."""
        key = self._make_key(name, tags)
        self._counters[key] = self._counters.get(key, 0) - value

    def get_counter(self, name: str, tags: dict[str, str] | None = None) -> int:
        """Get counter value."""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0)

    # =========================================================================
    # Gauge Operations
    # =========================================================================

    def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, tags)
        self._gauges[key] = value

        # Check alert thresholds
        if key in self._alert_thresholds:
            if value > self._alert_thresholds[key]:
                self._trigger_alert(key, value)

    def get_gauge(self, name: str, tags: dict[str, str] | None = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, tags)
        return self._gauges.get(key, 0.0)

    # =========================================================================
    # Timer Operations
    # =========================================================================

    def record_time(self, name: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        """Record a timing measurement."""
        key = self._make_key(name, tags)

        if key not in self._timers:
            self._timers[key] = deque(maxlen=self._history_size)

        self._timers[key].append(duration_ms)

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None):
        """Context manager for timing code blocks."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.record_time(name, duration_ms, tags)

    @asynccontextmanager
    async def async_timer(self, name: str, tags: dict[str, str] | None = None):
        """Async context manager for timing code blocks."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.record_time(name, duration_ms, tags)

    def get_timer_stats(self, name: str, tags: dict[str, str] | None = None) -> TimerStats:
        """Get timer statistics."""
        key = self._make_key(name, tags)
        times = list(self._timers.get(key, []))

        if not times:
            return TimerStats(name=name)

        sorted_times = sorted(times)
        count = len(times)

        return TimerStats(
            name=name,
            count=count,
            total_ms=sum(times),
            min_ms=min(times),
            max_ms=max(times),
            avg_ms=sum(times) / count,
            p50_ms=self._percentile(sorted_times, 50),
            p90_ms=self._percentile(sorted_times, 90),
            p95_ms=self._percentile(sorted_times, 95),
            p99_ms=self._percentile(sorted_times, 99),
        )

    # =========================================================================
    # Request Tracking
    # =========================================================================

    def record_request(
        self,
        duration_ms: float,
        success: bool = True,
        timeout: bool = False,
    ) -> None:
        """Record an API request."""
        self._request_count += 1
        self._request_times.append(duration_ms)

        if not success:
            self._request_errors += 1
        if timeout:
            self._request_timeouts += 1

    @contextmanager
    def track_request(self):
        """Context manager for tracking requests."""
        start = time.perf_counter()
        success = True
        timeout = False

        try:
            yield
        except asyncio.TimeoutError:
            success = False
            timeout = True
            raise
        except Exception:
            success = False
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.record_request(duration_ms, success, timeout)

    # =========================================================================
    # Span/Trace Operations
    # =========================================================================

    def start_span(self, name: str) -> str:
        """Start a timing span."""
        span_id = f"{name}:{uuid4().hex[:8]}"
        self._active_spans[span_id] = time.perf_counter()
        return span_id

    def end_span(self, span_id: str) -> float:
        """End a timing span and return duration."""
        if span_id not in self._active_spans:
            return 0.0

        start = self._active_spans.pop(span_id)
        duration_ms = (time.perf_counter() - start) * 1000

        # Extract name from span_id
        name = span_id.split(":")[0]
        self.record_time(name, duration_ms)

        return duration_ms

    # =========================================================================
    # Histogram Operations
    # =========================================================================

    def record_histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a value for histogram analysis."""
        key = self._make_key(name, tags)

        if key not in self._histograms:
            self._histograms[key] = []

        self._histograms[key].append(value)

        # Limit size
        if len(self._histograms[key]) > self._history_size:
            self._histograms[key] = self._histograms[key][-self._history_size:]

    def get_histogram_buckets(
        self,
        name: str,
        bucket_boundaries: list[float],
        tags: dict[str, str] | None = None,
    ) -> list[HistogramBucket]:
        """Get histogram bucket counts."""
        key = self._make_key(name, tags)
        values = self._histograms.get(key, [])

        buckets = []
        for boundary in sorted(bucket_boundaries):
            count = sum(1 for v in values if v <= boundary)
            buckets.append(HistogramBucket(le=boundary, count=count))

        # Add infinity bucket
        buckets.append(HistogramBucket(le=float("inf"), count=len(values)))

        return buckets

    # =========================================================================
    # Alerts
    # =========================================================================

    def set_alert_threshold(self, metric_name: str, threshold: float) -> None:
        """Set alert threshold for a metric."""
        self._alert_thresholds[metric_name] = threshold

    def add_alert_callback(self, callback: Callable[[str, float], None]) -> None:
        """Add callback for alert notifications."""
        self._alert_callbacks.append(callback)

    def _trigger_alert(self, metric_name: str, value: float) -> None:
        """Trigger alert callbacks."""
        for callback in self._alert_callbacks:
            try:
                callback(metric_name, value)
            except Exception:
                pass  # Don't let callback errors affect monitoring

    # =========================================================================
    # Aggregated Metrics
    # =========================================================================

    def get_metrics(self) -> PerformanceMetrics:
        """Get aggregated performance metrics."""
        request_times = list(self._request_times)
        elapsed = time.perf_counter() - self._start_time

        # Calculate request metrics
        if request_times:
            sorted_times = sorted(request_times)
            avg_response = sum(request_times) / len(request_times)
            p95_response = self._percentile(sorted_times, 95)
            p99_response = self._percentile(sorted_times, 99)
        else:
            avg_response = 0.0
            p95_response = 0.0
            p99_response = 0.0

        rps = self._request_count / elapsed if elapsed > 0 else 0.0

        error_rate = (
            self._request_errors / self._request_count * 100
            if self._request_count > 0 else 0.0
        )

        timeout_rate = (
            self._request_timeouts / self._request_count * 100
            if self._request_count > 0 else 0.0
        )

        # Collect timer stats
        timer_stats = {}
        for key in self._timers:
            name = key.split("|")[0]  # Remove tags
            timer_stats[name] = self.get_timer_stats(name)

        return PerformanceMetrics(
            total_requests=self._request_count,
            successful_requests=self._request_count - self._request_errors,
            failed_requests=self._request_errors,
            avg_response_time_ms=avg_response,
            p95_response_time_ms=p95_response,
            p99_response_time_ms=p99_response,
            requests_per_second=rps,
            active_connections=self.get_gauge("active_connections"),
            cache_hit_rate=self.get_gauge("cache_hit_rate"),
            memory_usage_mb=self.get_gauge("memory_usage_mb"),
            error_rate=error_rate,
            timeout_rate=timeout_rate,
            timers=timer_stats,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _make_key(self, name: str, tags: dict[str, str] | None = None) -> str:
        """Create unique key from name and tags."""
        if not tags:
            return name

        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}|{tag_str}"

    def _percentile(self, sorted_values: list[float], p: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * p / 100
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()
        self._histograms.clear()
        self._request_times.clear()
        self._request_errors = 0
        self._request_timeouts = 0
        self._request_count = 0
        self._start_time = time.perf_counter()
        self._active_spans.clear()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Counters
        for key, value in self._counters.items():
            name = key.replace("|", "_").replace(",", "_").replace("=", "_")
            lines.append(f"{name} {value}")

        # Gauges
        for key, value in self._gauges.items():
            name = key.replace("|", "_").replace(",", "_").replace("=", "_")
            lines.append(f"{name} {value}")

        # Timer summaries
        for key in self._timers:
            name = key.replace("|", "_").replace(",", "_").replace("=", "_")
            stats = self.get_timer_stats(key.split("|")[0])
            lines.append(f"{name}_count {stats.count}")
            lines.append(f"{name}_sum {stats.total_ms}")
            lines.append(f'{name}{{quantile="0.5"}} {stats.p50_ms}')
            lines.append(f'{name}{{quantile="0.9"}} {stats.p90_ms}')
            lines.append(f'{name}{{quantile="0.95"}} {stats.p95_ms}')
            lines.append(f'{name}{{quantile="0.99"}} {stats.p99_ms}')

        return "\n".join(lines)


# =============================================================================
# Factory Functions
# =============================================================================


_performance_monitor: PerformanceMonitor | None = None


def get_performance_monitor(history_size: int = 10000) -> PerformanceMonitor:
    """Get singleton PerformanceMonitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(history_size)
    return _performance_monitor


def create_performance_monitor(history_size: int = 10000) -> PerformanceMonitor:
    """Create new PerformanceMonitor instance."""
    return PerformanceMonitor(history_size)
