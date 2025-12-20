"""
Load Testing Suite.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides load testing utilities for performance benchmarking.
"""

import asyncio
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class LoadPattern(str, Enum):
    """Load test patterns."""

    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    WAVE = "wave"


@dataclass
class LoadTestConfig:
    """Load test configuration."""

    duration_seconds: float = 60.0
    target_rps: float = 100.0  # Requests per second
    concurrent_users: int = 10
    ramp_up_seconds: float = 10.0
    pattern: LoadPattern = LoadPattern.CONSTANT
    think_time_min: float = 0.0  # Seconds between requests
    think_time_max: float = 0.0


@dataclass
class RequestResult:
    """Single request result."""

    success: bool
    duration_ms: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadTestResult:
    """Load test aggregate results."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_seconds: float = 0.0

    # Timing metrics
    min_response_ms: float = float("inf")
    max_response_ms: float = 0.0
    avg_response_ms: float = 0.0
    median_response_ms: float = 0.0
    p90_response_ms: float = 0.0
    p95_response_ms: float = 0.0
    p99_response_ms: float = 0.0
    std_dev_ms: float = 0.0

    # Throughput
    actual_rps: float = 0.0
    target_rps: float = 0.0

    # Error analysis
    error_rate: float = 0.0
    errors_by_type: dict[str, int] = field(default_factory=dict)

    # Timing breakdown
    response_times: list[float] = field(default_factory=list)


class LoadTester:
    """Load testing service."""

    def __init__(self, config: LoadTestConfig | None = None):
        """Initialize LoadTester."""
        self._config = config or LoadTestConfig()
        self._results: list[RequestResult] = []
        self._running = False
        self._start_time: Optional[float] = None

    @property
    def config(self) -> LoadTestConfig:
        """Get configuration."""
        return self._config

    async def run(
        self,
        request_func: Callable[[], Any],
        config: LoadTestConfig | None = None,
    ) -> LoadTestResult:
        """Run load test.

        Args:
            request_func: Async callable to execute for each request
            config: Optional override configuration
        """
        cfg = config or self._config
        self._results = []
        self._running = True
        self._start_time = time.perf_counter()

        # Create worker tasks
        workers = []
        for i in range(cfg.concurrent_users):
            worker = asyncio.create_task(
                self._worker(request_func, cfg, i)
            )
            workers.append(worker)

        # Run for duration
        try:
            await asyncio.wait_for(
                asyncio.gather(*workers, return_exceptions=True),
                timeout=cfg.duration_seconds + cfg.ramp_up_seconds + 5.0,
            )
        except asyncio.TimeoutError:
            pass
        finally:
            self._running = False

        return self._calculate_results(cfg)

    async def _worker(
        self,
        request_func: Callable[[], Any],
        config: LoadTestConfig,
        worker_id: int,
    ) -> None:
        """Worker that executes requests."""
        # Calculate ramp-up delay for this worker
        if config.pattern == LoadPattern.RAMP_UP and config.ramp_up_seconds > 0:
            delay = (worker_id / config.concurrent_users) * config.ramp_up_seconds
            await asyncio.sleep(delay)

        interval = config.concurrent_users / config.target_rps

        while self._running:
            elapsed = time.perf_counter() - self._start_time

            if elapsed >= config.duration_seconds:
                break

            # Apply load pattern
            current_load = self._get_current_load(config, elapsed)

            # Execute request
            start = time.perf_counter()
            success = True
            error: Optional[str] = None
            status_code: Optional[int] = None

            try:
                if asyncio.iscoroutinefunction(request_func):
                    result = await request_func()
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, request_func
                    )

                # Check for status code if returned
                if hasattr(result, "status_code"):
                    status_code = result.status_code
                    success = 200 <= status_code < 400

            except Exception as e:
                success = False
                error = str(e)

            duration_ms = (time.perf_counter() - start) * 1000

            self._results.append(RequestResult(
                success=success,
                duration_ms=duration_ms,
                status_code=status_code,
                error=error,
            ))

            # Think time
            if config.think_time_max > 0:
                think_time = random.uniform(
                    config.think_time_min,
                    config.think_time_max,
                )
                await asyncio.sleep(think_time)

            # Rate limiting based on load pattern
            adjusted_interval = interval / current_load if current_load > 0 else interval
            await asyncio.sleep(max(0, adjusted_interval - (duration_ms / 1000)))

    def _get_current_load(self, config: LoadTestConfig, elapsed: float) -> float:
        """Get current load multiplier based on pattern."""
        if config.pattern == LoadPattern.CONSTANT:
            return 1.0

        elif config.pattern == LoadPattern.RAMP_UP:
            if elapsed < config.ramp_up_seconds:
                return elapsed / config.ramp_up_seconds
            return 1.0

        elif config.pattern == LoadPattern.SPIKE:
            # Spike at midpoint
            midpoint = config.duration_seconds / 2
            if midpoint - 5 < elapsed < midpoint + 5:
                return 3.0  # Triple load during spike
            return 1.0

        elif config.pattern == LoadPattern.WAVE:
            # Sinusoidal pattern
            import math
            return 0.5 + 0.5 * math.sin(elapsed * math.pi / 15)  # 30-second period

        return 1.0

    def _calculate_results(self, config: LoadTestConfig) -> LoadTestResult:
        """Calculate aggregate results."""
        if not self._results:
            return LoadTestResult(target_rps=config.target_rps)

        successful = [r for r in self._results if r.success]
        failed = [r for r in self._results if not r.success]
        response_times = [r.duration_ms for r in self._results]

        total_duration = time.perf_counter() - self._start_time

        # Calculate percentiles
        sorted_times = sorted(response_times)

        def percentile(data: list[float], p: float) -> float:
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1
            if c >= len(data):
                return data[-1]
            return data[f] + (k - f) * (data[c] - data[f])

        # Error analysis
        errors_by_type: dict[str, int] = {}
        for r in failed:
            error_type = r.error or f"HTTP {r.status_code}" if r.status_code else "Unknown"
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1

        return LoadTestResult(
            total_requests=len(self._results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_duration_seconds=total_duration,
            min_response_ms=min(response_times) if response_times else 0.0,
            max_response_ms=max(response_times) if response_times else 0.0,
            avg_response_ms=statistics.mean(response_times) if response_times else 0.0,
            median_response_ms=statistics.median(response_times) if response_times else 0.0,
            p90_response_ms=percentile(sorted_times, 90) if sorted_times else 0.0,
            p95_response_ms=percentile(sorted_times, 95) if sorted_times else 0.0,
            p99_response_ms=percentile(sorted_times, 99) if sorted_times else 0.0,
            std_dev_ms=statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
            actual_rps=len(self._results) / total_duration if total_duration > 0 else 0.0,
            target_rps=config.target_rps,
            error_rate=len(failed) / len(self._results) * 100 if self._results else 0.0,
            errors_by_type=errors_by_type,
            response_times=response_times,
        )

    def stop(self) -> None:
        """Stop the load test."""
        self._running = False


def print_results(result: LoadTestResult) -> None:
    """Print load test results in a readable format."""
    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)

    print(f"\nRequests:")
    print(f"  Total:      {result.total_requests}")
    print(f"  Successful: {result.successful_requests}")
    print(f"  Failed:     {result.failed_requests}")
    print(f"  Error Rate: {result.error_rate:.2f}%")

    print(f"\nThroughput:")
    print(f"  Target RPS: {result.target_rps:.1f}")
    print(f"  Actual RPS: {result.actual_rps:.1f}")
    print(f"  Duration:   {result.total_duration_seconds:.1f}s")

    print(f"\nResponse Times (ms):")
    print(f"  Min:    {result.min_response_ms:.2f}")
    print(f"  Max:    {result.max_response_ms:.2f}")
    print(f"  Avg:    {result.avg_response_ms:.2f}")
    print(f"  Median: {result.median_response_ms:.2f}")
    print(f"  P90:    {result.p90_response_ms:.2f}")
    print(f"  P95:    {result.p95_response_ms:.2f}")
    print(f"  P99:    {result.p99_response_ms:.2f}")
    print(f"  StdDev: {result.std_dev_ms:.2f}")

    if result.errors_by_type:
        print(f"\nErrors by Type:")
        for error_type, count in result.errors_by_type.items():
            print(f"  {error_type}: {count}")

    print("\n" + "=" * 60)


# Benchmark utilities
async def benchmark_function(
    func: Callable[[], Any],
    iterations: int = 100,
    warmup: int = 10,
) -> dict[str, float]:
    """Benchmark a function.

    Args:
        func: Function to benchmark
        iterations: Number of iterations
        warmup: Warmup iterations (not counted)

    Returns:
        Dictionary with timing statistics
    """
    # Warmup
    for _ in range(warmup):
        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()

        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()

        times.append((time.perf_counter() - start) * 1000)

    sorted_times = sorted(times)

    def percentile(data: list[float], p: float) -> float:
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= len(data):
            return data[-1]
        return data[f] + (k - f) * (data[c] - data[f])

    return {
        "iterations": iterations,
        "min_ms": min(times),
        "max_ms": max(times),
        "avg_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p95_ms": percentile(sorted_times, 95),
        "p99_ms": percentile(sorted_times, 99),
        "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
        "ops_per_second": 1000 / statistics.mean(times) if times else 0.0,
    }
