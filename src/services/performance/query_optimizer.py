"""
Query Optimizer Service.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides database query optimization hints and analysis.
"""

import re
import time
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class OptimizationLevel(str, Enum):
    """Query optimization level."""

    NONE = "none"
    BASIC = "basic"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class QueryType(str, Enum):
    """SQL query type."""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


class IndexSuggestion(BaseModel):
    """Index suggestion for query optimization."""

    table: str
    columns: list[str]
    index_type: str = "btree"
    reason: str
    estimated_improvement: float  # Percentage


class OptimizationHint(BaseModel):
    """Query optimization hint."""

    hint_type: str
    description: str
    severity: str  # info, warning, critical
    suggestion: str
    code_location: Optional[str] = None


class QueryPlan(BaseModel):
    """Query execution plan analysis."""

    query: str
    query_type: QueryType
    estimated_rows: int = 0
    estimated_cost: float = 0.0
    uses_index: bool = False
    index_names: list[str] = Field(default_factory=list)
    sequential_scans: int = 0
    hints: list[OptimizationHint] = Field(default_factory=list)
    index_suggestions: list[IndexSuggestion] = Field(default_factory=list)
    optimized_query: Optional[str] = None
    analysis_time_ms: float = 0.0


class QueryStats(BaseModel):
    """Query execution statistics."""

    query_hash: str
    query_pattern: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    rows_affected: int = 0
    last_executed: datetime = Field(default_factory=datetime.utcnow)


class QueryOptimizer:
    """Database query optimizer service."""

    def __init__(self, level: OptimizationLevel = OptimizationLevel.MODERATE):
        """Initialize QueryOptimizer."""
        self._level = level
        self._query_stats: dict[str, QueryStats] = {}
        self._slow_query_threshold_ms = 1000.0

        # Common optimization patterns
        self._optimization_patterns = [
            (
                r"SELECT \* FROM",
                "Avoid SELECT *",
                "Select only required columns to reduce I/O",
            ),
            (
                r"WHERE.*LIKE '%[^%]",
                "Leading wildcard in LIKE",
                "Leading wildcards prevent index usage; consider full-text search",
            ),
            (
                r"ORDER BY.*RAND\(\)",
                "Random ordering",
                "ORDER BY RAND() is slow; use application-level randomization",
            ),
            (
                r"WHERE.*!=|WHERE.*<>",
                "Negative comparisons",
                "NOT EQUAL operators may prevent index usage",
            ),
            (
                r"WHERE.*OR.*OR.*OR",
                "Multiple OR conditions",
                "Consider using IN clause or UNION for better performance",
            ),
            (
                r"SELECT.*FROM.*,.*,.*,",
                "Multiple implicit joins",
                "Use explicit JOIN syntax for clarity and optimization",
            ),
            (
                r"WHERE.*IN\s*\([^)]{500,}",
                "Large IN clause",
                "Very large IN clauses are slow; consider temporary table or JOIN",
            ),
            (
                r"WHERE\s+\w+\s*\(\s*\w+\s*\)",
                "Function on indexed column",
                "Functions on columns prevent index usage; restructure query",
            ),
        ]

    @property
    def level(self) -> OptimizationLevel:
        """Get optimization level."""
        return self._level

    def set_level(self, level: OptimizationLevel) -> None:
        """Set optimization level."""
        self._level = level

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect SQL query type."""
        normalized = query.strip().upper()

        if normalized.startswith("SELECT"):
            return QueryType.SELECT
        elif normalized.startswith("INSERT"):
            return QueryType.INSERT
        elif normalized.startswith("UPDATE"):
            return QueryType.UPDATE
        elif normalized.startswith("DELETE"):
            return QueryType.DELETE
        else:
            return QueryType.OTHER

    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", query.strip())

        # Replace literal values with placeholders
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r"\b\d+\b", "?", normalized)

        return normalized

    def _hash_query(self, query: str) -> str:
        """Create hash for query pattern."""
        import hashlib

        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def analyze(self, query: str) -> QueryPlan:
        """Analyze query and provide optimization hints."""
        start = time.perf_counter()

        query_type = self._detect_query_type(query)
        hints: list[OptimizationHint] = []
        index_suggestions: list[IndexSuggestion] = []

        # Pattern-based analysis
        query_upper = query.upper()

        for pattern, hint_type, suggestion in self._optimization_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                hints.append(OptimizationHint(
                    hint_type=hint_type,
                    description=f"Pattern detected: {hint_type}",
                    severity="warning",
                    suggestion=suggestion,
                ))

        # Check for missing WHERE clause in UPDATE/DELETE
        if query_type in [QueryType.UPDATE, QueryType.DELETE]:
            if "WHERE" not in query_upper:
                hints.append(OptimizationHint(
                    hint_type="Missing WHERE clause",
                    description="UPDATE/DELETE without WHERE affects all rows",
                    severity="critical",
                    suggestion="Add WHERE clause to limit affected rows",
                ))

        # Check for N+1 query patterns
        if "SELECT" in query_upper and query_upper.count("SELECT") > 1:
            hints.append(OptimizationHint(
                hint_type="Subquery detected",
                description="Subqueries may cause N+1 issues",
                severity="info",
                suggestion="Consider JOINs or CTEs for better performance",
            ))

        # Index suggestions based on WHERE/JOIN columns
        where_columns = self._extract_where_columns(query)
        join_columns = self._extract_join_columns(query)

        for col in where_columns:
            if col not in join_columns:
                table = self._guess_table_for_column(query, col)
                if table:
                    index_suggestions.append(IndexSuggestion(
                        table=table,
                        columns=[col],
                        index_type="btree",
                        reason=f"Column {col} used in WHERE clause",
                        estimated_improvement=20.0,
                    ))

        # Generate optimized query if applicable
        optimized = self._optimize_query(query) if self._level != OptimizationLevel.NONE else None

        analysis_time = (time.perf_counter() - start) * 1000

        return QueryPlan(
            query=query,
            query_type=query_type,
            estimated_rows=0,  # Would need EXPLAIN for actual estimate
            estimated_cost=0.0,
            uses_index=False,  # Would need EXPLAIN
            sequential_scans=0,
            hints=hints,
            index_suggestions=index_suggestions,
            optimized_query=optimized,
            analysis_time_ms=analysis_time,
        )

    def _extract_where_columns(self, query: str) -> list[str]:
        """Extract column names from WHERE clause."""
        columns = []

        # Simple extraction - would need SQL parser for accuracy
        where_match = re.search(r"WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)", query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # Extract column names before operators
            col_matches = re.findall(r"(\w+)\s*[=<>!]", where_clause)
            columns.extend(col_matches)

        return list(set(columns))

    def _extract_join_columns(self, query: str) -> list[str]:
        """Extract column names from JOIN conditions."""
        columns = []

        join_matches = re.findall(r"JOIN.+?ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", query, re.IGNORECASE)
        for match in join_matches:
            columns.extend([match[1], match[3]])

        return list(set(columns))

    def _guess_table_for_column(self, query: str, column: str) -> Optional[str]:
        """Guess which table a column belongs to."""
        # Look for table.column pattern
        match = re.search(rf"(\w+)\.{column}", query, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for FROM clause
        from_match = re.search(r"FROM\s+(\w+)", query, re.IGNORECASE)
        if from_match:
            return from_match.group(1)

        return None

    def _optimize_query(self, query: str) -> Optional[str]:
        """Apply optimizations to query."""
        optimized = query

        if self._level == OptimizationLevel.BASIC:
            # Just clean up whitespace
            optimized = re.sub(r"\s+", " ", optimized.strip())

        elif self._level in [OptimizationLevel.MODERATE, OptimizationLevel.AGGRESSIVE]:
            # Replace SELECT * with explicit columns (would need schema)
            # This is a simplified example
            optimized = re.sub(r"\s+", " ", optimized.strip())

            # Convert implicit joins to explicit
            if "," in query.split("FROM")[-1].split("WHERE")[0] if "FROM" in query else "":
                pass  # Would need SQL parser for safe conversion

        return optimized if optimized != query else None

    def record_execution(
        self,
        query: str,
        execution_time_ms: float,
        rows_affected: int = 0,
    ) -> None:
        """Record query execution statistics."""
        query_hash = self._hash_query(query)
        query_pattern = self._normalize_query(query)

        if query_hash in self._query_stats:
            stats = self._query_stats[query_hash]
            stats.execution_count += 1
            stats.total_time_ms += execution_time_ms
            stats.avg_time_ms = stats.total_time_ms / stats.execution_count
            stats.min_time_ms = min(stats.min_time_ms, execution_time_ms)
            stats.max_time_ms = max(stats.max_time_ms, execution_time_ms)
            stats.rows_affected += rows_affected
            stats.last_executed = datetime.utcnow()
        else:
            self._query_stats[query_hash] = QueryStats(
                query_hash=query_hash,
                query_pattern=query_pattern,
                execution_count=1,
                total_time_ms=execution_time_ms,
                avg_time_ms=execution_time_ms,
                min_time_ms=execution_time_ms,
                max_time_ms=execution_time_ms,
                rows_affected=rows_affected,
            )

    def get_slow_queries(
        self,
        threshold_ms: float | None = None,
        limit: int = 10,
    ) -> list[QueryStats]:
        """Get slow queries above threshold."""
        threshold = threshold_ms or self._slow_query_threshold_ms

        slow = [
            stats for stats in self._query_stats.values()
            if stats.avg_time_ms > threshold
        ]

        return sorted(slow, key=lambda s: s.avg_time_ms, reverse=True)[:limit]

    def get_frequent_queries(self, limit: int = 10) -> list[QueryStats]:
        """Get most frequently executed queries."""
        return sorted(
            self._query_stats.values(),
            key=lambda s: s.execution_count,
            reverse=True,
        )[:limit]

    def get_query_stats(self, query: str) -> Optional[QueryStats]:
        """Get statistics for a specific query."""
        query_hash = self._hash_query(query)
        return self._query_stats.get(query_hash)

    def clear_stats(self) -> None:
        """Clear all query statistics."""
        self._query_stats.clear()


# =============================================================================
# Factory Functions
# =============================================================================


_query_optimizer: QueryOptimizer | None = None


def get_query_optimizer(
    level: OptimizationLevel = OptimizationLevel.MODERATE,
) -> QueryOptimizer:
    """Get singleton QueryOptimizer instance."""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer(level)
    return _query_optimizer


def create_query_optimizer(
    level: OptimizationLevel = OptimizationLevel.MODERATE,
) -> QueryOptimizer:
    """Create new QueryOptimizer instance."""
    return QueryOptimizer(level)
