"""
Validation Performance Service.

Source: Design Document 04_validation_engine_comprehensive_design.md
Phase 5.4: Performance Optimization

Provides performance optimizations specific to the validation engine:
- Typesense query caching
- Connection pooling for search services
- Parallel execution optimization
- Validation-specific performance monitoring

Target metrics:
- Single claim: <2s p95
- Batch processing: <30s for 100 claims
- Typesense search: <50ms p95
- LLM extraction: <5s p95
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar

from pydantic import BaseModel, Field

from src.services.performance.cache import (
    CacheService,
    CacheConfig,
    CacheBackend,
    get_cache_service,
    cached,
)
from src.services.performance.connection_pool import (
    ConnectionPool,
    PoolConfig,
    get_connection_pool,
)
from src.services.performance.monitor import (
    PerformanceMonitor,
    get_performance_monitor,
    TimerStats,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Configuration
# =============================================================================


class ValidationPerformanceConfig(BaseModel):
    """Performance configuration for validation engine."""

    # Cache settings
    typesense_cache_ttl: int = 3600  # 1 hour for code lookups
    crosswalk_cache_ttl: int = 86400  # 24 hours for crosswalk data
    llm_response_cache_ttl: int = 300  # 5 min for LLM responses
    max_cache_items: int = 10000

    # Connection pool settings
    typesense_pool_min: int = 5
    typesense_pool_max: int = 20
    llm_pool_min: int = 2
    llm_pool_max: int = 10
    pool_max_idle_time: int = 300
    pool_acquire_timeout: float = 10.0

    # Parallel execution settings
    max_concurrent_rules: int = 8
    batch_size: int = 50
    batch_processing_workers: int = 4

    # Monitoring thresholds
    slow_query_threshold_ms: float = 100.0
    slow_validation_threshold_ms: float = 2000.0
    slow_llm_threshold_ms: float = 5000.0

    # Alert thresholds
    cache_hit_rate_alert_threshold: float = 50.0  # Alert if <50% hit rate
    error_rate_alert_threshold: float = 5.0  # Alert if >5% errors
    p95_latency_alert_threshold_ms: float = 2500.0  # Alert if p95 >2.5s


# =============================================================================
# Validation Cache Service
# =============================================================================


class ValidationCacheService:
    """
    Specialized caching service for validation operations.

    Provides tiered caching with different TTLs for:
    - Medical code lookups (ICD-10, CPT)
    - Crosswalk data
    - LLM responses
    """

    def __init__(self, config: ValidationPerformanceConfig | None = None):
        """Initialize ValidationCacheService."""
        self._config = config or ValidationPerformanceConfig()

        # Separate cache namespaces for different data types
        self._code_cache = CacheService(CacheConfig(
            backend=CacheBackend.TIERED,
            default_ttl=self._config.typesense_cache_ttl,
            max_memory_items=self._config.max_cache_items // 2,
            key_prefix="val:code:",
        ))

        self._crosswalk_cache = CacheService(CacheConfig(
            backend=CacheBackend.TIERED,
            default_ttl=self._config.crosswalk_cache_ttl,
            max_memory_items=self._config.max_cache_items // 4,
            key_prefix="val:xwalk:",
        ))

        self._llm_cache = CacheService(CacheConfig(
            backend=CacheBackend.MEMORY,  # Memory only for LLM (less persistence)
            default_ttl=self._config.llm_response_cache_ttl,
            max_memory_items=self._config.max_cache_items // 4,
            key_prefix="val:llm:",
        ))

        self._monitor = get_performance_monitor()

    # =========================================================================
    # Code Lookup Cache
    # =========================================================================

    async def get_icd_code(self, code: str) -> Optional[dict]:
        """Get cached ICD code data."""
        key = f"icd:{code.upper()}"
        result = await self._code_cache.get(key)
        if result:
            self._monitor.increment("cache_hit", tags={"type": "icd"})
        else:
            self._monitor.increment("cache_miss", tags={"type": "icd"})
        return result

    async def set_icd_code(self, code: str, data: dict) -> None:
        """Cache ICD code data."""
        key = f"icd:{code.upper()}"
        await self._code_cache.set(key, data, self._config.typesense_cache_ttl)

    async def get_cpt_code(self, code: str) -> Optional[dict]:
        """Get cached CPT code data."""
        key = f"cpt:{code}"
        result = await self._code_cache.get(key)
        if result:
            self._monitor.increment("cache_hit", tags={"type": "cpt"})
        else:
            self._monitor.increment("cache_miss", tags={"type": "cpt"})
        return result

    async def set_cpt_code(self, code: str, data: dict) -> None:
        """Cache CPT code data."""
        key = f"cpt:{code}"
        await self._code_cache.set(key, data, self._config.typesense_cache_ttl)

    async def get_or_fetch_code(
        self,
        code: str,
        code_type: str,
        fetch_fn: Callable[[], Any],
    ) -> Optional[dict]:
        """Get code from cache or fetch and cache."""
        if code_type == "icd":
            cached = await self.get_icd_code(code)
            if cached:
                return cached
            result = await fetch_fn() if asyncio.iscoroutinefunction(fetch_fn) else fetch_fn()
            if result:
                await self.set_icd_code(code, result)
            return result
        elif code_type == "cpt":
            cached = await self.get_cpt_code(code)
            if cached:
                return cached
            result = await fetch_fn() if asyncio.iscoroutinefunction(fetch_fn) else fetch_fn()
            if result:
                await self.set_cpt_code(code, result)
            return result
        return None

    # =========================================================================
    # Crosswalk Cache
    # =========================================================================

    async def get_crosswalk(self, icd_code: str, cpt_code: str) -> Optional[dict]:
        """Get cached crosswalk data."""
        key = f"{icd_code.upper()}:{cpt_code}"
        result = await self._crosswalk_cache.get(key)
        if result:
            self._monitor.increment("cache_hit", tags={"type": "crosswalk"})
        else:
            self._monitor.increment("cache_miss", tags={"type": "crosswalk"})
        return result

    async def set_crosswalk(self, icd_code: str, cpt_code: str, data: dict) -> None:
        """Cache crosswalk data."""
        key = f"{icd_code.upper()}:{cpt_code}"
        await self._crosswalk_cache.set(key, data, self._config.crosswalk_cache_ttl)

    async def get_icd_cpt_associations(self, icd_code: str) -> Optional[list[str]]:
        """Get cached CPT codes associated with an ICD code."""
        key = f"assoc:icd:{icd_code.upper()}"
        return await self._crosswalk_cache.get(key)

    async def set_icd_cpt_associations(self, icd_code: str, cpt_codes: list[str]) -> None:
        """Cache CPT codes associated with an ICD code."""
        key = f"assoc:icd:{icd_code.upper()}"
        await self._crosswalk_cache.set(key, cpt_codes, self._config.crosswalk_cache_ttl)

    # =========================================================================
    # LLM Response Cache
    # =========================================================================

    def _hash_llm_input(self, prompt: str, context: dict | None = None) -> str:
        """Create hash key for LLM input."""
        content = {"prompt": prompt, "context": context or {}}
        serialized = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:32]

    async def get_llm_response(
        self,
        prompt: str,
        context: dict | None = None,
    ) -> Optional[dict]:
        """Get cached LLM response."""
        key = self._hash_llm_input(prompt, context)
        result = await self._llm_cache.get(key)
        if result:
            self._monitor.increment("cache_hit", tags={"type": "llm"})
        else:
            self._monitor.increment("cache_miss", tags={"type": "llm"})
        return result

    async def set_llm_response(
        self,
        prompt: str,
        response: dict,
        context: dict | None = None,
    ) -> None:
        """Cache LLM response."""
        key = self._hash_llm_input(prompt, context)
        await self._llm_cache.set(key, response, self._config.llm_response_cache_ttl)

    # =========================================================================
    # Cache Management
    # =========================================================================

    async def clear_all(self) -> None:
        """Clear all validation caches."""
        await self._code_cache.clear()
        await self._crosswalk_cache.clear()
        await self._llm_cache.clear()

    async def clear_code_cache(self) -> None:
        """Clear code lookup cache."""
        await self._code_cache.clear()

    async def clear_crosswalk_cache(self) -> None:
        """Clear crosswalk cache."""
        await self._crosswalk_cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "code_cache": self._code_cache.get_stats().model_dump(),
            "crosswalk_cache": self._crosswalk_cache.get_stats().model_dump(),
            "llm_cache": self._llm_cache.get_stats().model_dump(),
        }


# =============================================================================
# Batch Processor
# =============================================================================


@dataclass
class BatchResult:
    """Result from batch processing."""

    total_items: int
    successful: int
    failed: int
    results: list[Any] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)
    execution_time_ms: int = 0


class BatchProcessor:
    """
    Optimized batch processing for validation operations.

    Features:
    - Parallel processing with configurable concurrency
    - Automatic batching
    - Progress tracking
    - Error isolation
    """

    def __init__(self, config: ValidationPerformanceConfig | None = None):
        """Initialize BatchProcessor."""
        self._config = config or ValidationPerformanceConfig()
        self._monitor = get_performance_monitor()
        self._semaphore = asyncio.Semaphore(self._config.batch_processing_workers)

    async def process_batch(
        self,
        items: list[Any],
        processor: Callable[[Any], Any],
        batch_name: str = "batch",
    ) -> BatchResult:
        """
        Process a batch of items with controlled parallelism.

        Args:
            items: Items to process
            processor: Async function to process each item
            batch_name: Name for monitoring

        Returns:
            BatchResult with all outcomes
        """
        import time
        start_time = time.perf_counter()

        results = []
        errors = []
        successful = 0
        failed = 0

        # Process in batches
        batch_size = self._config.batch_size

        async def process_item(index: int, item: Any) -> tuple[int, Any, Optional[str]]:
            async with self._semaphore:
                try:
                    if asyncio.iscoroutinefunction(processor):
                        result = await processor(item)
                    else:
                        result = processor(item)
                    return index, result, None
                except Exception as e:
                    return index, None, str(e)

        # Create all tasks
        tasks = [process_item(i, item) for i, item in enumerate(items)]

        # Process in batches
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch_tasks)

            for idx, result, error in batch_results:
                if error:
                    failed += 1
                    errors.append((idx, error))
                else:
                    successful += 1
                    results.append((idx, result))

        execution_time = int((time.perf_counter() - start_time) * 1000)

        # Record metrics
        self._monitor.record_time(f"batch_{batch_name}", execution_time)
        self._monitor.increment(f"batch_{batch_name}_total", len(items))
        self._monitor.increment(f"batch_{batch_name}_success", successful)
        self._monitor.increment(f"batch_{batch_name}_failed", failed)

        # Sort results by original index
        sorted_results = [r for _, r in sorted(results, key=lambda x: x[0])]

        return BatchResult(
            total_items=len(items),
            successful=successful,
            failed=failed,
            results=sorted_results,
            errors=errors,
            execution_time_ms=execution_time,
        )

    async def process_claims_batch(
        self,
        claim_inputs: list[Any],
        validator: Callable[[Any], Any],
    ) -> BatchResult:
        """Process a batch of claims for validation."""
        return await self.process_batch(
            items=claim_inputs,
            processor=validator,
            batch_name="claim_validation",
        )


# =============================================================================
# Validation Performance Monitor
# =============================================================================


class ValidationPerformanceMonitor:
    """
    Specialized performance monitoring for validation engine.

    Tracks:
    - Validation timing by rule and phase
    - Cache effectiveness
    - Error rates
    - SLA compliance
    """

    def __init__(self, config: ValidationPerformanceConfig | None = None):
        """Initialize ValidationPerformanceMonitor."""
        self._config = config or ValidationPerformanceConfig()
        self._monitor = get_performance_monitor()

        # Set up alert thresholds
        self._monitor.set_alert_threshold(
            "validation_p95_ms",
            self._config.p95_latency_alert_threshold_ms,
        )
        self._monitor.set_alert_threshold(
            "cache_hit_rate",
            self._config.cache_hit_rate_alert_threshold,
        )

        # Validation counters
        self._validations_total = 0
        self._validations_passed = 0
        self._validations_failed = 0
        self._validations_error = 0

        # SLA tracking
        self._sla_violations = 0

    # =========================================================================
    # Validation Tracking
    # =========================================================================

    def record_validation(
        self,
        claim_id: str,
        duration_ms: float,
        passed: bool,
        rule_count: int,
        error: bool = False,
    ) -> None:
        """Record a validation completion."""
        self._validations_total += 1

        if error:
            self._validations_error += 1
        elif passed:
            self._validations_passed += 1
        else:
            self._validations_failed += 1

        # Record timing
        self._monitor.record_time("validation_total", duration_ms)

        # Check SLA
        if duration_ms > self._config.slow_validation_threshold_ms:
            self._sla_violations += 1
            self._monitor.increment("sla_violation", tags={"type": "slow_validation"})
            logger.warning(
                f"Slow validation: claim={claim_id}, duration={duration_ms:.0f}ms"
            )

        # Record histogram for latency distribution
        self._monitor.record_histogram("validation_latency", duration_ms)

    def record_rule_execution(
        self,
        rule_id: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record individual rule execution."""
        self._monitor.record_time(f"rule_{rule_id}", duration_ms)
        self._monitor.increment(
            f"rule_{rule_id}_count",
            tags={"status": "success" if success else "failure"},
        )

    def record_typesense_query(
        self,
        query_type: str,
        duration_ms: float,
        hit_count: int = 0,
    ) -> None:
        """Record Typesense query performance."""
        self._monitor.record_time(f"typesense_{query_type}", duration_ms)

        if duration_ms > self._config.slow_query_threshold_ms:
            self._monitor.increment("slow_query", tags={"type": query_type})
            logger.debug(
                f"Slow Typesense query: type={query_type}, duration={duration_ms:.0f}ms"
            )

    def record_llm_call(
        self,
        operation: str,
        duration_ms: float,
        tokens_used: int = 0,
        cached: bool = False,
    ) -> None:
        """Record LLM API call performance."""
        self._monitor.record_time(f"llm_{operation}", duration_ms)
        self._monitor.increment(f"llm_{operation}_count")

        if tokens_used > 0:
            self._monitor.record_histogram("llm_tokens", tokens_used)

        if cached:
            self._monitor.increment("llm_cache_hit")

        if duration_ms > self._config.slow_llm_threshold_ms:
            self._monitor.increment("slow_llm", tags={"operation": operation})

    # =========================================================================
    # Metrics Export
    # =========================================================================

    def get_validation_metrics(self) -> dict:
        """Get validation-specific metrics."""
        total = self._validations_total or 1  # Avoid division by zero

        validation_stats = self._monitor.get_timer_stats("validation_total")

        return {
            "validations": {
                "total": self._validations_total,
                "passed": self._validations_passed,
                "failed": self._validations_failed,
                "errors": self._validations_error,
                "pass_rate": (self._validations_passed / total) * 100,
                "error_rate": (self._validations_error / total) * 100,
            },
            "timing": {
                "avg_ms": validation_stats.avg_ms,
                "p50_ms": validation_stats.p50_ms,
                "p95_ms": validation_stats.p95_ms,
                "p99_ms": validation_stats.p99_ms,
                "min_ms": validation_stats.min_ms if validation_stats.count > 0 else 0,
                "max_ms": validation_stats.max_ms if validation_stats.count > 0 else 0,
            },
            "sla": {
                "target_ms": self._config.slow_validation_threshold_ms,
                "violations": self._sla_violations,
                "compliance_rate": ((total - self._sla_violations) / total) * 100,
            },
        }

    def get_rule_metrics(self) -> dict[str, TimerStats]:
        """Get per-rule performance metrics."""
        rule_ids = [
            "rule_1", "rule_2", "rule_3", "rule_4", "rule_5",
            "rule_6", "rule_7_8", "rule_9",
        ]

        return {
            rule_id: self._monitor.get_timer_stats(f"rule_{rule_id}")
            for rule_id in rule_ids
        }

    def get_cache_metrics(self) -> dict:
        """Get cache performance metrics."""
        cache_types = ["icd", "cpt", "crosswalk", "llm"]
        metrics = {}

        for cache_type in cache_types:
            hits = self._monitor.get_counter("cache_hit", tags={"type": cache_type})
            misses = self._monitor.get_counter("cache_miss", tags={"type": cache_type})
            total = hits + misses or 1

            metrics[cache_type] = {
                "hits": hits,
                "misses": misses,
                "hit_rate": (hits / total) * 100,
            }

        return metrics

    def reset(self) -> None:
        """Reset all metrics."""
        self._validations_total = 0
        self._validations_passed = 0
        self._validations_failed = 0
        self._validations_error = 0
        self._sla_violations = 0


# =============================================================================
# Parallel Execution Optimizer
# =============================================================================


class ParallelExecutor:
    """
    Optimized parallel execution for validation rules.

    Features:
    - Controlled concurrency
    - Dependency-aware scheduling
    - Timeout handling
    - Result aggregation
    """

    def __init__(self, config: ValidationPerformanceConfig | None = None):
        """Initialize ParallelExecutor."""
        self._config = config or ValidationPerformanceConfig()
        self._semaphore = asyncio.Semaphore(self._config.max_concurrent_rules)
        self._monitor = get_performance_monitor()

    async def execute_parallel(
        self,
        tasks: list[tuple[str, Callable[[], Any]]],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Execute multiple tasks in parallel with controlled concurrency.

        Args:
            tasks: List of (name, async_callable) tuples
            timeout: Overall timeout in seconds

        Returns:
            Dictionary of task_name -> result
        """
        results = {}
        errors = {}

        async def run_task(name: str, task_fn: Callable[[], Any]) -> tuple[str, Any, Optional[str]]:
            async with self._semaphore:
                start = asyncio.get_event_loop().time()
                try:
                    if asyncio.iscoroutinefunction(task_fn):
                        result = await asyncio.wait_for(task_fn(), timeout=timeout)
                    else:
                        result = task_fn()
                    duration_ms = (asyncio.get_event_loop().time() - start) * 1000
                    self._monitor.record_time(f"parallel_{name}", duration_ms)
                    return name, result, None
                except asyncio.TimeoutError:
                    return name, None, f"Task '{name}' timed out"
                except Exception as e:
                    return name, None, str(e)

        # Run all tasks
        task_coroutines = [run_task(name, fn) for name, fn in tasks]

        try:
            completed = await asyncio.wait_for(
                asyncio.gather(*task_coroutines, return_exceptions=True),
                timeout=timeout,
            )

            for item in completed:
                if isinstance(item, Exception):
                    logger.error(f"Parallel task error: {item}")
                else:
                    name, result, error = item
                    if error:
                        errors[name] = error
                    else:
                        results[name] = result

        except asyncio.TimeoutError:
            logger.error("Overall parallel execution timeout")

        if errors:
            results["_errors"] = errors

        return results

    async def execute_with_dependencies(
        self,
        task_graph: dict[str, tuple[Callable[[], Any], list[str]]],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Execute tasks respecting dependencies.

        Args:
            task_graph: Dict of task_name -> (callable, dependencies)
            timeout: Overall timeout

        Returns:
            Dictionary of task_name -> result
        """
        results = {}
        completed = set()
        pending = set(task_graph.keys())

        async def can_run(task_name: str) -> bool:
            _, deps = task_graph[task_name]
            return all(d in completed for d in deps)

        while pending:
            # Find tasks that can run now
            runnable = [t for t in pending if await can_run(t)]

            if not runnable:
                # No progress possible - circular dependency or all done
                break

            # Run all runnable tasks in parallel
            tasks = [(name, task_graph[name][0]) for name in runnable]
            batch_results = await self.execute_parallel(tasks, timeout)

            # Update state
            for name in runnable:
                pending.discard(name)
                completed.add(name)
                if name in batch_results:
                    results[name] = batch_results[name]

        return results


# =============================================================================
# Factory Functions
# =============================================================================


_validation_cache: ValidationCacheService | None = None
_batch_processor: BatchProcessor | None = None
_performance_monitor: ValidationPerformanceMonitor | None = None
_parallel_executor: ParallelExecutor | None = None


def get_validation_cache(
    config: ValidationPerformanceConfig | None = None,
) -> ValidationCacheService:
    """Get or create singleton ValidationCacheService."""
    global _validation_cache
    if _validation_cache is None:
        _validation_cache = ValidationCacheService(config)
    return _validation_cache


def get_batch_processor(
    config: ValidationPerformanceConfig | None = None,
) -> BatchProcessor:
    """Get or create singleton BatchProcessor."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor(config)
    return _batch_processor


def get_validation_performance_monitor(
    config: ValidationPerformanceConfig | None = None,
) -> ValidationPerformanceMonitor:
    """Get or create singleton ValidationPerformanceMonitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = ValidationPerformanceMonitor(config)
    return _performance_monitor


def get_parallel_executor(
    config: ValidationPerformanceConfig | None = None,
) -> ParallelExecutor:
    """Get or create singleton ParallelExecutor."""
    global _parallel_executor
    if _parallel_executor is None:
        _parallel_executor = ParallelExecutor(config)
    return _parallel_executor


# =============================================================================
# Decorators
# =============================================================================


def monitor_validation(func: Callable) -> Callable:
    """Decorator to monitor validation function performance."""
    import functools
    import time

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        monitor = get_validation_performance_monitor()
        start = time.perf_counter()
        error = False

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error = True
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            # Extract claim_id if available
            claim_id = kwargs.get("claim_id", "unknown")
            if hasattr(args[0] if args else None, "claim_id"):
                claim_id = args[0].claim_id
            monitor.record_validation(
                claim_id=claim_id,
                duration_ms=duration_ms,
                passed=not error,
                rule_count=0,
                error=error,
            )

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            async_wrapper(*args, **kwargs)
        )

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def cache_code_lookup(code_type: str, ttl: int | None = None):
    """Decorator to cache code lookup results."""
    def decorator(func: Callable) -> Callable:
        import functools

        @functools.wraps(func)
        async def wrapper(code: str, *args, **kwargs):
            cache = get_validation_cache()

            # Check cache
            if code_type == "icd":
                cached = await cache.get_icd_code(code)
                if cached:
                    return cached
            elif code_type == "cpt":
                cached = await cache.get_cpt_code(code)
                if cached:
                    return cached

            # Execute function
            result = await func(code, *args, **kwargs)

            # Cache result
            if result:
                if code_type == "icd":
                    await cache.set_icd_code(code, result)
                elif code_type == "cpt":
                    await cache.set_cpt_code(code, result)

            return result

        return wrapper
    return decorator
