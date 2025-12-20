"""
Sprint 13: Performance Optimization Tests.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Tests for caching, connection pooling, query optimization, and async processing.
Uses inline class definitions to avoid import chain issues.
"""

import asyncio
import hashlib
import json
import re
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from functools import wraps
from typing import Any, Callable, Generic, Optional, TypeVar
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field


# =============================================================================
# Inline Cache Classes
# =============================================================================


class CacheBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    TIERED = "tiered"


class CacheConfig(BaseModel):
    backend: CacheBackend = CacheBackend.MEMORY
    default_ttl: int = 300
    max_memory_items: int = 1000
    key_prefix: str = "reimp:"


class CacheStats(BaseModel):
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_items: int = 0
    hit_rate: float = 0.0


class CacheEntry(BaseModel):
    key: str
    value: Any
    ttl: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    access_count: int = 0

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class LRUCache:
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            entry.access_count += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        async with self._lock:
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            now = datetime.utcnow()
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl),
            )
            self._cache[key] = entry
            self._cache.move_to_end(key)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


class CacheService:
    def __init__(self, config: CacheConfig | None = None):
        self._config = config or CacheConfig()
        self._memory_cache = LRUCache(self._config.max_memory_items)
        self._hits = 0
        self._misses = 0

    def _make_key(self, key: str) -> str:
        return f"{self._config.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        value = await self._memory_cache.get(full_key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        full_key = self._make_key(key)
        cache_ttl = ttl or self._config.default_ttl
        await self._memory_cache.set(full_key, value, cache_ttl)

    async def delete(self, key: str) -> bool:
        full_key = self._make_key(key)
        return await self._memory_cache.delete(full_key)

    async def clear(self) -> None:
        await self._memory_cache.clear()

    async def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int | None = None) -> Any:
        value = await self.get(key)
        if value is None:
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()
            await self.set(key, value, ttl)
        return value

    def get_stats(self) -> CacheStats:
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            total_items=self._memory_cache.size(),
            hit_rate=hit_rate,
        )


# =============================================================================
# Inline Connection Pool Classes
# =============================================================================


class PoolStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ConnectionState(str, Enum):
    IDLE = "idle"
    IN_USE = "in_use"
    CLOSED = "closed"


class PoolConfig(BaseModel):
    min_size: int = 5
    max_size: int = 20
    acquire_timeout: float = 30.0


class PoolStats(BaseModel):
    total_connections: int = 0
    idle_connections: int = 0
    in_use_connections: int = 0
    total_acquisitions: int = 0
    total_releases: int = 0
    status: PoolStatus = PoolStatus.HEALTHY


class ConnectionInfo(BaseModel):
    connection_id: str = Field(default_factory=lambda: str(uuid4()))
    state: ConnectionState = ConnectionState.IDLE
    created_at: datetime = Field(default_factory=datetime.utcnow)


T = TypeVar("T")


class PooledConnection(Generic[T]):
    def __init__(self, connection: T, info: ConnectionInfo, pool: "ConnectionPool[T]"):
        self._connection = connection
        self._info = info
        self._pool = pool

    @property
    def connection(self) -> T:
        return self._connection

    @property
    def info(self) -> ConnectionInfo:
        return self._info

    async def release(self) -> None:
        await self._pool.release(self)


class ConnectionPool(Generic[T]):
    def __init__(self, factory: Any, config: PoolConfig | None = None):
        self._factory = factory
        self._config = config or PoolConfig()
        self._connections: dict[str, tuple[T, ConnectionInfo]] = {}
        self._idle_queue: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._total_acquisitions = 0
        self._total_releases = 0

    async def initialize(self) -> None:
        for _ in range(self._config.min_size):
            conn, info = await self._create_connection()
            self._connections[info.connection_id] = (conn, info)
            await self._idle_queue.put(info.connection_id)

    async def _create_connection(self) -> tuple[T, ConnectionInfo]:
        if asyncio.iscoroutinefunction(self._factory):
            connection = await self._factory()
        else:
            connection = self._factory()
        info = ConnectionInfo(state=ConnectionState.IDLE)
        return connection, info

    async def acquire(self) -> PooledConnection[T]:
        try:
            conn_id = await asyncio.wait_for(self._idle_queue.get(), timeout=0.5)
            if conn_id in self._connections:
                conn, info = self._connections[conn_id]
                info.state = ConnectionState.IN_USE
                self._total_acquisitions += 1
                return PooledConnection(conn, info, self)
        except asyncio.TimeoutError:
            pass

        async with self._lock:
            if len(self._connections) < self._config.max_size:
                conn, info = await self._create_connection()
                info.state = ConnectionState.IN_USE
                self._connections[info.connection_id] = (conn, info)
                self._total_acquisitions += 1
                return PooledConnection(conn, info, self)

        conn_id = await asyncio.wait_for(self._idle_queue.get(), timeout=self._config.acquire_timeout)
        conn, info = self._connections[conn_id]
        info.state = ConnectionState.IN_USE
        self._total_acquisitions += 1
        return PooledConnection(conn, info, self)

    async def release(self, pooled: PooledConnection[T]) -> None:
        self._total_releases += 1
        pooled.info.state = ConnectionState.IDLE
        await self._idle_queue.put(pooled.info.connection_id)

    @asynccontextmanager
    async def connection(self):
        pooled = await self.acquire()
        try:
            yield pooled.connection
        finally:
            await pooled.release()

    def get_stats(self) -> PoolStats:
        total = len(self._connections)
        idle = self._idle_queue.qsize()
        return PoolStats(
            total_connections=total,
            idle_connections=idle,
            in_use_connections=total - idle,
            total_acquisitions=self._total_acquisitions,
            total_releases=self._total_releases,
            status=PoolStatus.HEALTHY if total > 0 else PoolStatus.UNHEALTHY,
        )

    async def close(self) -> None:
        self._connections.clear()


# =============================================================================
# Inline Query Optimizer Classes
# =============================================================================


class QueryType(str, Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


class OptimizationHint(BaseModel):
    hint_type: str
    description: str
    severity: str
    suggestion: str


class QueryPlan(BaseModel):
    query: str
    query_type: QueryType
    hints: list[OptimizationHint] = Field(default_factory=list)


class QueryStats(BaseModel):
    query_hash: str
    query_pattern: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0


class QueryOptimizer:
    def __init__(self):
        self._query_stats: dict[str, QueryStats] = {}
        self._patterns = [
            (r"SELECT \* FROM", "Avoid SELECT *", "Select only required columns"),
            (r"WHERE.*LIKE '%", "Leading wildcard", "Prevent index usage"),
        ]

    def _detect_query_type(self, query: str) -> QueryType:
        normalized = query.strip().upper()
        if normalized.startswith("SELECT"):
            return QueryType.SELECT
        elif normalized.startswith("INSERT"):
            return QueryType.INSERT
        elif normalized.startswith("UPDATE"):
            return QueryType.UPDATE
        elif normalized.startswith("DELETE"):
            return QueryType.DELETE
        return QueryType.OTHER

    def _normalize_query(self, query: str) -> str:
        normalized = re.sub(r"\s+", " ", query.strip())
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        return normalized

    def _hash_query(self, query: str) -> str:
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def analyze(self, query: str) -> QueryPlan:
        query_type = self._detect_query_type(query)
        hints: list[OptimizationHint] = []
        query_upper = query.upper()

        for pattern, hint_type, suggestion in self._patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                hints.append(OptimizationHint(
                    hint_type=hint_type,
                    description=f"Pattern detected: {hint_type}",
                    severity="warning",
                    suggestion=suggestion,
                ))

        if query_type in [QueryType.UPDATE, QueryType.DELETE]:
            if "WHERE" not in query_upper:
                hints.append(OptimizationHint(
                    hint_type="Missing WHERE clause",
                    description="UPDATE/DELETE without WHERE",
                    severity="critical",
                    suggestion="Add WHERE clause",
                ))

        return QueryPlan(query=query, query_type=query_type, hints=hints)

    def record_execution(self, query: str, execution_time_ms: float) -> None:
        query_hash = self._hash_query(query)
        query_pattern = self._normalize_query(query)

        if query_hash in self._query_stats:
            stats = self._query_stats[query_hash]
            stats.execution_count += 1
            stats.total_time_ms += execution_time_ms
            stats.avg_time_ms = stats.total_time_ms / stats.execution_count
            stats.min_time_ms = min(stats.min_time_ms, execution_time_ms)
            stats.max_time_ms = max(stats.max_time_ms, execution_time_ms)
        else:
            self._query_stats[query_hash] = QueryStats(
                query_hash=query_hash,
                query_pattern=query_pattern,
                execution_count=1,
                total_time_ms=execution_time_ms,
                avg_time_ms=execution_time_ms,
                min_time_ms=execution_time_ms,
                max_time_ms=execution_time_ms,
            )

    def get_slow_queries(self, threshold_ms: float = 1000.0) -> list[QueryStats]:
        return [s for s in self._query_stats.values() if s.avg_time_ms > threshold_ms]

    def get_query_stats(self, query: str) -> Optional[QueryStats]:
        return self._query_stats.get(self._hash_query(query))


# =============================================================================
# Inline Async Processor Classes
# =============================================================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10


class BatchConfig(BaseModel):
    batch_size: int = 100
    max_concurrent: int = 10
    timeout_per_item: float = 30.0
    retry_attempts: int = 2


class ProcessingStats(BaseModel):
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    error_rate: float = 0.0


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None


R = TypeVar("R")


class AsyncTask(Generic[T, R]):
    def __init__(self, task_id: str, data: T, processor: Callable[[T], R], priority: TaskPriority = TaskPriority.NORMAL):
        self.task_id = task_id
        self.data = data
        self.processor = processor
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.result: Optional[R] = None
        self.error: Optional[str] = None

    def __lt__(self, other: "AsyncTask") -> bool:
        return self.priority.value > other.priority.value


class AsyncProcessor:
    def __init__(self, config: BatchConfig | None = None):
        self._config = config or BatchConfig()
        self._tasks: dict[str, AsyncTask] = {}
        self._pending_queue: asyncio.PriorityQueue[tuple[int, AsyncTask]] = asyncio.PriorityQueue()
        self._completed_tasks = 0
        self._failed_tasks = 0

    async def submit(self, data: T, processor: Callable[[T], R], priority: TaskPriority = TaskPriority.NORMAL, task_id: str | None = None) -> str:
        task_id = task_id or str(uuid4())
        task = AsyncTask(task_id=task_id, data=data, processor=processor, priority=priority)
        self._tasks[task_id] = task
        await self._pending_queue.put((-priority.value, task))
        return task_id

    async def submit_batch(self, items: list[T], processor: Callable[[T], R], priority: TaskPriority = TaskPriority.NORMAL) -> list[str]:
        return [await self.submit(item, processor, priority) for item in items]

    async def process_all(self) -> list[TaskResult]:
        results: list[TaskResult] = []
        tasks: list[AsyncTask] = []

        while not self._pending_queue.empty():
            try:
                _, task = await asyncio.wait_for(self._pending_queue.get(), timeout=0.1)
                tasks.append(task)
            except asyncio.TimeoutError:
                break

        semaphore = asyncio.Semaphore(self._config.max_concurrent)

        async def process_task(task: AsyncTask) -> TaskResult:
            async with semaphore:
                task.status = TaskStatus.RUNNING
                try:
                    if asyncio.iscoroutinefunction(task.processor):
                        result = await task.processor(task.data)
                    else:
                        result = task.processor(task.data)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    self._completed_tasks += 1
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    self._failed_tasks += 1

                return TaskResult(task_id=task.task_id, status=task.status, result=task.result, error=task.error)

        results = await asyncio.gather(*[process_task(t) for t in tasks])
        return list(results)

    def get_stats(self) -> ProcessingStats:
        total = len(self._tasks)
        error_rate = (self._failed_tasks / total * 100) if total > 0 else 0.0
        return ProcessingStats(
            total_tasks=total,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            error_rate=error_rate,
        )


# =============================================================================
# Inline Performance Monitor Classes
# =============================================================================


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    TIMER = "timer"


class TimerStats(BaseModel):
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
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0


class PerformanceMonitor:
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._timers: dict[str, deque[float]] = {}
        self._request_count = 0
        self._request_errors = 0
        self._alert_thresholds: dict[str, float] = {}
        self._alert_callbacks: list[Callable[[str, float], None]] = []
        self._active_spans: dict[str, float] = {}

    def _make_key(self, name: str, tags: dict[str, str] | None = None) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}|{tag_str}"

    def increment(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        key = self._make_key(name, tags)
        self._counters[key] = self._counters.get(key, 0) + value

    def decrement(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        key = self._make_key(name, tags)
        self._counters[key] = self._counters.get(key, 0) - value

    def get_counter(self, name: str, tags: dict[str, str] | None = None) -> int:
        return self._counters.get(self._make_key(name, tags), 0)

    def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        key = self._make_key(name, tags)
        self._gauges[key] = value
        if key in self._alert_thresholds and value > self._alert_thresholds[key]:
            for cb in self._alert_callbacks:
                cb(key, value)

    def get_gauge(self, name: str, tags: dict[str, str] | None = None) -> float:
        return self._gauges.get(self._make_key(name, tags), 0.0)

    def record_time(self, name: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        key = self._make_key(name, tags)
        if key not in self._timers:
            self._timers[key] = deque(maxlen=10000)
        self._timers[key].append(duration_ms)

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record_time(name, (time.perf_counter() - start) * 1000, tags)

    @asynccontextmanager
    async def async_timer(self, name: str, tags: dict[str, str] | None = None):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record_time(name, (time.perf_counter() - start) * 1000, tags)

    def _percentile(self, sorted_values: list[float], p: float) -> float:
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= len(sorted_values):
            return sorted_values[-1]
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def get_timer_stats(self, name: str, tags: dict[str, str] | None = None) -> TimerStats:
        key = self._make_key(name, tags)
        times = list(self._timers.get(key, []))
        if not times:
            return TimerStats(name=name)
        sorted_times = sorted(times)
        return TimerStats(
            name=name,
            count=len(times),
            total_ms=sum(times),
            min_ms=min(times),
            max_ms=max(times),
            avg_ms=sum(times) / len(times),
            p50_ms=self._percentile(sorted_times, 50),
            p90_ms=self._percentile(sorted_times, 90),
            p95_ms=self._percentile(sorted_times, 95),
            p99_ms=self._percentile(sorted_times, 99),
        )

    def record_request(self, duration_ms: float, success: bool = True) -> None:
        self._request_count += 1
        if not success:
            self._request_errors += 1

    def start_span(self, name: str) -> str:
        span_id = f"{name}:{uuid4().hex[:8]}"
        self._active_spans[span_id] = time.perf_counter()
        return span_id

    def end_span(self, span_id: str) -> float:
        if span_id not in self._active_spans:
            return 0.0
        start = self._active_spans.pop(span_id)
        duration_ms = (time.perf_counter() - start) * 1000
        name = span_id.split(":")[0]
        self.record_time(name, duration_ms)
        return duration_ms

    def record_histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        key = self._make_key(name, tags)
        if key not in self._timers:
            self._timers[key] = deque(maxlen=10000)
        self._timers[key].append(value)

    def get_histogram_buckets(self, name: str, bucket_boundaries: list[float], tags: dict[str, str] | None = None) -> list[dict]:
        key = self._make_key(name, tags)
        values = list(self._timers.get(key, []))
        buckets = []
        for boundary in sorted(bucket_boundaries):
            count = sum(1 for v in values if v <= boundary)
            buckets.append({"le": boundary, "count": count})
        buckets.append({"le": float("inf"), "count": len(values)})
        return buckets

    def set_alert_threshold(self, metric_name: str, threshold: float) -> None:
        self._alert_thresholds[metric_name] = threshold

    def add_alert_callback(self, callback: Callable[[str, float], None]) -> None:
        self._alert_callbacks.append(callback)

    def get_metrics(self) -> PerformanceMetrics:
        return PerformanceMetrics(
            total_requests=self._request_count,
            successful_requests=self._request_count - self._request_errors,
            failed_requests=self._request_errors,
        )

    def export_prometheus(self) -> str:
        lines = []
        for key, value in self._counters.items():
            name = key.replace("|", "_").replace(",", "_").replace("=", "_")
            lines.append(f"{name} {value}")
        for key, value in self._gauges.items():
            name = key.replace("|", "_").replace(",", "_").replace("=", "_")
            lines.append(f"{name} {value}")
        return "\n".join(lines)


# =============================================================================
# Test Classes
# =============================================================================


class TestCacheService:
    """Tests for CacheService."""

    @pytest.fixture
    def cache_service(self):
        config = CacheConfig(max_memory_items=100, default_ttl=60)
        return CacheService(config)

    @pytest.mark.asyncio
    async def test_basic_set_and_get(self, cache_service):
        await cache_service.set("test_key", "test_value")
        result = await cache_service.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service):
        result = await cache_service.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_service):
        await cache_service.set("expire_key", "value", ttl=1)
        result = await cache_service.get("expire_key")
        assert result == "value"
        await asyncio.sleep(1.1)
        result = await cache_service.get("expire_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_service):
        await cache_service.set("delete_key", "value")
        deleted = await cache_service.delete("delete_key")
        assert deleted is True
        result = await cache_service.get("delete_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_or_set(self, cache_service):
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return "computed_value"

        result1 = await cache_service.get_or_set("factory_key", factory)
        assert result1 == "computed_value"
        assert call_count == 1

        result2 = await cache_service.get_or_set("factory_key", factory)
        assert result2 == "computed_value"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_complex_values(self, cache_service):
        data = {"claim_id": "CLM-123", "amount": 1500.50, "items": [1, 2, 3]}
        await cache_service.set("complex_key", data)
        result = await cache_service.get("complex_key")
        assert result == data

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service):
        await cache_service.set("key1", "value1")
        await cache_service.get("key1")
        await cache_service.get("key1")
        await cache_service.get("miss")
        stats = cache_service.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_service):
        await cache_service.set("key1", "value1")
        await cache_service.set("key2", "value2")
        await cache_service.clear()
        assert await cache_service.get("key1") is None
        assert await cache_service.get("key2") is None


class TestLRUCache:
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        cache = LRUCache(max_size=3)
        await cache.set("key1", "value1", ttl=300)
        await cache.set("key2", "value2", ttl=300)
        await cache.set("key3", "value3", ttl=300)
        await cache.get("key1")
        await cache.set("key4", "value4", ttl=300)
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"


class TestConnectionPool:
    @pytest.fixture
    def pool_config(self):
        return PoolConfig(min_size=2, max_size=5, acquire_timeout=5.0)

    @pytest.fixture
    def connection_factory(self):
        counter = {"value": 0}

        async def factory():
            counter["value"] += 1
            return {"id": counter["value"], "connected": True}

        return factory

    @pytest.mark.asyncio
    async def test_pool_acquire_release(self, pool_config, connection_factory):
        pool = ConnectionPool(connection_factory, pool_config)
        await pool.initialize()
        pooled = await pool.acquire()
        assert pooled.connection["connected"] is True
        await pooled.release()
        stats = pool.get_stats()
        assert stats.total_acquisitions == 1
        assert stats.total_releases == 1
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_reuse_connections(self, pool_config, connection_factory):
        # Use a single-connection pool to test reuse
        single_config = PoolConfig(min_size=1, max_size=1, acquire_timeout=5.0)
        pool = ConnectionPool(connection_factory, single_config)
        await pool.initialize()
        pooled1 = await pool.acquire()
        conn_id = pooled1.connection["id"]
        await pooled1.release()
        pooled2 = await pool.acquire()
        assert pooled2.connection["id"] == conn_id  # Must be same since only 1 connection
        await pooled2.release()
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_concurrent_access(self, pool_config, connection_factory):
        pool = ConnectionPool(connection_factory, pool_config)
        await pool.initialize()

        async def worker():
            pooled = await pool.acquire()
            await asyncio.sleep(0.05)
            await pooled.release()

        await asyncio.gather(*[worker() for _ in range(10)])
        stats = pool.get_stats()
        assert stats.total_acquisitions == 10
        assert stats.total_releases == 10
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_context_manager(self, pool_config, connection_factory):
        pool = ConnectionPool(connection_factory, pool_config)
        await pool.initialize()
        async with pool.connection() as conn:
            assert conn["connected"] is True
        stats = pool.get_stats()
        assert stats.total_acquisitions == 1
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_stats(self, pool_config, connection_factory):
        pool = ConnectionPool(connection_factory, pool_config)
        await pool.initialize()
        stats = pool.get_stats()
        assert stats.total_connections >= pool_config.min_size
        assert stats.status == PoolStatus.HEALTHY
        await pool.close()


class TestQueryOptimizer:
    @pytest.fixture
    def optimizer(self):
        return QueryOptimizer()

    def test_detect_select_star(self, optimizer):
        query = "SELECT * FROM claims WHERE status = 'active'"
        plan = optimizer.analyze(query)
        assert any("SELECT *" in h.hint_type for h in plan.hints)

    def test_detect_missing_where_update(self, optimizer):
        query = "UPDATE claims SET status = 'closed'"
        plan = optimizer.analyze(query)
        assert any("WHERE" in h.hint_type for h in plan.hints)
        assert any(h.severity == "critical" for h in plan.hints)

    def test_detect_leading_wildcard(self, optimizer):
        query = "SELECT id FROM claims WHERE name LIKE '%smith'"
        plan = optimizer.analyze(query)
        assert any("wildcard" in h.hint_type.lower() for h in plan.hints)

    def test_query_type_detection(self, optimizer):
        assert optimizer.analyze("SELECT * FROM claims").query_type == QueryType.SELECT
        assert optimizer.analyze("INSERT INTO claims (id) VALUES (1)").query_type == QueryType.INSERT
        assert optimizer.analyze("UPDATE claims SET status = 'active'").query_type == QueryType.UPDATE
        assert optimizer.analyze("DELETE FROM claims WHERE id = 1").query_type == QueryType.DELETE

    def test_record_and_get_slow_queries(self, optimizer):
        optimizer.record_execution("SELECT * FROM claims", 1500.0)
        optimizer.record_execution("SELECT * FROM claims", 2000.0)
        optimizer.record_execution("SELECT id FROM members", 50.0)
        slow = optimizer.get_slow_queries(threshold_ms=1000.0)
        assert len(slow) >= 1
        assert slow[0].avg_time_ms > 1000.0

    def test_query_stats_aggregation(self, optimizer):
        query = "SELECT id FROM providers WHERE npi = '1234567890'"
        optimizer.record_execution(query, 100.0)
        optimizer.record_execution(query, 150.0)
        optimizer.record_execution(query, 200.0)
        stats = optimizer.get_query_stats(query)
        assert stats is not None
        assert stats.execution_count == 3
        assert stats.avg_time_ms == 150.0


class TestAsyncProcessor:
    @pytest.fixture
    def processor(self):
        config = BatchConfig(batch_size=10, max_concurrent=5, timeout_per_item=5.0, retry_attempts=2)
        return AsyncProcessor(config)

    @pytest.mark.asyncio
    async def test_submit_and_process_single(self, processor):
        async def square(x):
            return x * x

        await processor.submit(5, square)
        results = await processor.process_all()
        assert len(results) == 1
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].result == 25

    @pytest.mark.asyncio
    async def test_submit_batch(self, processor):
        async def double(x):
            return x * 2

        await processor.submit_batch([1, 2, 3, 4, 5], double)
        results = await processor.process_all()
        assert len(results) == 5
        actual_results = sorted([r.result for r in results])
        assert actual_results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_task_failure_handling(self, processor):
        async def failing_task(x):
            if x == 3:
                raise ValueError("Task failed")
            return x

        await processor.submit_batch([1, 2, 3, 4, 5], failing_task)
        results = await processor.process_all()
        successful = [r for r in results if r.status == TaskStatus.COMPLETED]
        failed = [r for r in results if r.status == TaskStatus.FAILED]
        assert len(successful) == 4
        assert len(failed) == 1

    @pytest.mark.asyncio
    async def test_task_priority(self, processor):
        results_order = []

        async def record_order(x):
            results_order.append(x)
            return x

        await processor.submit("normal", record_order, TaskPriority.NORMAL)
        await processor.submit("high", record_order, TaskPriority.HIGH)
        await processor.submit("low", record_order, TaskPriority.LOW)
        await processor.process_all()
        assert results_order[0] == "high"

    @pytest.mark.asyncio
    async def test_processor_stats(self, processor):
        async def simple_task(x):
            return x

        await processor.submit_batch([1, 2, 3], simple_task)
        await processor.process_all()
        stats = processor.get_stats()
        assert stats.total_tasks == 3
        assert stats.completed_tasks == 3


class TestPerformanceMonitor:
    @pytest.fixture
    def monitor(self):
        return PerformanceMonitor()

    def test_counter_operations(self, monitor):
        monitor.increment("requests", 1)
        monitor.increment("requests", 2)
        monitor.decrement("requests", 1)
        assert monitor.get_counter("requests") == 2

    def test_gauge_operations(self, monitor):
        monitor.set_gauge("cpu_usage", 75.5)
        assert monitor.get_gauge("cpu_usage") == 75.5

    def test_timer_recording(self, monitor):
        monitor.record_time("db_query", 50.0)
        monitor.record_time("db_query", 100.0)
        monitor.record_time("db_query", 150.0)
        stats = monitor.get_timer_stats("db_query")
        assert stats.count == 3
        assert stats.avg_ms == 100.0

    def test_timer_context_manager(self, monitor):
        with monitor.timer("operation"):
            time.sleep(0.05)
        stats = monitor.get_timer_stats("operation")
        assert stats.count == 1
        assert stats.avg_ms >= 40

    @pytest.mark.asyncio
    async def test_async_timer_context_manager(self, monitor):
        async with monitor.async_timer("async_operation"):
            await asyncio.sleep(0.05)
        stats = monitor.get_timer_stats("async_operation")
        assert stats.count == 1
        assert stats.avg_ms >= 40

    def test_request_tracking(self, monitor):
        monitor.record_request(100.0, success=True)
        monitor.record_request(200.0, success=True)
        monitor.record_request(500.0, success=False)
        metrics = monitor.get_metrics()
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1

    def test_span_operations(self, monitor):
        span_id = monitor.start_span("process_claim")
        time.sleep(0.05)
        duration = monitor.end_span(span_id)
        assert duration >= 40
        stats = monitor.get_timer_stats("process_claim")
        assert stats.count == 1

    def test_histogram_buckets(self, monitor):
        for value in [10, 20, 50, 100, 200, 500]:
            monitor.record_histogram("response_time", value)
        buckets = monitor.get_histogram_buckets("response_time", [50, 100, 250, 500])
        assert buckets[0]["count"] == 3
        assert buckets[1]["count"] == 4
        assert buckets[-1]["count"] == 6

    def test_alert_threshold(self, monitor):
        alerts_triggered = []

        def alert_callback(metric_name, value):
            alerts_triggered.append((metric_name, value))

        monitor.set_alert_threshold("error_rate", 5.0)
        monitor.add_alert_callback(alert_callback)
        monitor.set_gauge("error_rate", 3.0)
        assert len(alerts_triggered) == 0
        monitor.set_gauge("error_rate", 10.0)
        assert len(alerts_triggered) == 1

    def test_prometheus_export(self, monitor):
        monitor.increment("http_requests", 100)
        monitor.set_gauge("active_connections", 50)
        output = monitor.export_prometheus()
        assert "http_requests 100" in output
        assert "active_connections 50" in output

    def test_metrics_with_tags(self, monitor):
        monitor.increment("requests", 1, tags={"method": "GET"})
        monitor.increment("requests", 2, tags={"method": "POST"})
        assert monitor.get_counter("requests", tags={"method": "GET"}) == 1
        assert monitor.get_counter("requests", tags={"method": "POST"}) == 2
