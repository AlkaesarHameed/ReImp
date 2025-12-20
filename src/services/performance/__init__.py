"""
Performance Optimization Services.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides caching, connection pooling, and performance monitoring.
"""

from src.services.performance.cache import (
    CacheService,
    CacheConfig,
    CacheStats,
    get_cache_service,
    cached,
)
from src.services.performance.connection_pool import (
    ConnectionPool,
    PoolConfig,
    PoolStats,
    get_connection_pool,
)
from src.services.performance.query_optimizer import (
    QueryOptimizer,
    QueryPlan,
    OptimizationHint,
    get_query_optimizer,
)
from src.services.performance.async_processor import (
    AsyncProcessor,
    BatchConfig,
    ProcessingStats,
    get_async_processor,
)
from src.services.performance.monitor import (
    PerformanceMonitor,
    MetricType,
    PerformanceMetrics,
    get_performance_monitor,
)


__all__ = [
    # Cache
    "CacheService",
    "CacheConfig",
    "CacheStats",
    "get_cache_service",
    "cached",
    # Connection Pool
    "ConnectionPool",
    "PoolConfig",
    "PoolStats",
    "get_connection_pool",
    # Query Optimizer
    "QueryOptimizer",
    "QueryPlan",
    "OptimizationHint",
    "get_query_optimizer",
    # Async Processor
    "AsyncProcessor",
    "BatchConfig",
    "ProcessingStats",
    "get_async_processor",
    # Monitor
    "PerformanceMonitor",
    "MetricType",
    "PerformanceMetrics",
    "get_performance_monitor",
]
