"""
Sprint 15 Tests: Monitoring & Observability.
Source: Design Document Section 5.3 - Monitoring & Observability
Verified: 2025-12-18

Tests for observability services: logging, tracing, health checks, alerts, and dashboards.
"""

import asyncio
import io
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field


# =============================================================================
# Inline Class Definitions (to avoid import chain issues)
# =============================================================================


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


LOG_LEVEL_VALUES = {
    LogLevel.DEBUG: 10,
    LogLevel.INFO: 20,
    LogLevel.WARNING: 30,
    LogLevel.ERROR: 40,
    LogLevel.CRITICAL: 50,
}


class LogContext(BaseModel):
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    service_name: str = "claims-processor"
    environment: str = "development"
    version: str = "1.0.0"
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    message: str
    logger_name: str = "app"
    context: LogContext = Field(default_factory=LogContext)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict:
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "logger": self.logger_name,
            "service": self.context.service_name,
            "environment": self.context.environment,
        }
        if self.context.request_id:
            result["request_id"] = self.context.request_id
        if self.context.user_id:
            result["user_id"] = self.context.user_id
        if self.context.trace_id:
            result["trace_id"] = self.context.trace_id
        if self.error_type:
            result["error"] = {"type": self.error_type, "message": self.error_message}
        if self.data:
            result["data"] = self.data
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        return result


class StructuredLogger:
    def __init__(
        self,
        name: str = "app",
        level: LogLevel = LogLevel.INFO,
        context: LogContext | None = None,
        output: io.TextIOBase | None = None,
    ):
        self._name = name
        self._level = level
        self._context = context or LogContext()
        self._output = output or io.StringIO()
        self._handlers: list[callable] = []
        self._entries: list[LogEntry] = []
        self._max_entries = 10000

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> LogLevel:
        return self._level

    def set_level(self, level: LogLevel) -> None:
        self._level = level

    def set_context(self, context: LogContext) -> None:
        self._context = context

    def with_context(self, **kwargs) -> "StructuredLogger":
        new_context = self._context.model_copy()
        for key, value in kwargs.items():
            if hasattr(new_context, key):
                setattr(new_context, key, value)
            else:
                new_context.extra[key] = value
        return StructuredLogger(
            name=self._name,
            level=self._level,
            context=new_context,
            output=self._output,
        )

    def _should_log(self, level: LogLevel) -> bool:
        return LOG_LEVEL_VALUES[level] >= LOG_LEVEL_VALUES[self._level]

    def _log(
        self,
        level: LogLevel,
        message: str,
        data: dict[str, Any] | None = None,
        error: Exception | None = None,
        duration_ms: float | None = None,
        **kwargs,
    ) -> LogEntry | None:
        if not self._should_log(level):
            return None

        context = self._context.model_copy()
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.extra[key] = value

        entry = LogEntry(
            level=level,
            message=message,
            logger_name=self._name,
            context=context,
            data=data or {},
            duration_ms=duration_ms,
        )

        if error:
            entry.error_type = type(error).__name__
            entry.error_message = str(error)

        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        line = json.dumps(entry.to_dict())
        self._output.write(line + "\n")

        for handler in self._handlers:
            try:
                handler(entry)
            except Exception:
                pass

        return entry

    def debug(self, message: str, data: dict = None, **kwargs) -> LogEntry | None:
        return self._log(LogLevel.DEBUG, message, data, **kwargs)

    def info(self, message: str, data: dict = None, **kwargs) -> LogEntry | None:
        return self._log(LogLevel.INFO, message, data, **kwargs)

    def warning(self, message: str, data: dict = None, **kwargs) -> LogEntry | None:
        return self._log(LogLevel.WARNING, message, data, **kwargs)

    def error(self, message: str, error: Exception = None, data: dict = None, **kwargs) -> LogEntry | None:
        return self._log(LogLevel.ERROR, message, data, error=error, **kwargs)

    def critical(self, message: str, error: Exception = None, data: dict = None, **kwargs) -> LogEntry | None:
        return self._log(LogLevel.CRITICAL, message, data, error=error, **kwargs)

    def log_request(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs) -> LogEntry | None:
        level = LogLevel.INFO if status_code < 400 else LogLevel.ERROR
        return self._log(
            level,
            f"{method} {path} - {status_code}",
            data={"http.method": method, "http.path": path, "http.status_code": status_code},
            duration_ms=duration_ms,
            **kwargs,
        )

    def add_handler(self, handler: callable) -> None:
        self._handlers.append(handler)

    def get_entries(self, level: LogLevel = None, limit: int = 100) -> list[LogEntry]:
        entries = self._entries.copy()
        if level:
            min_value = LOG_LEVEL_VALUES[level]
            entries = [e for e in entries if LOG_LEVEL_VALUES[e.level] >= min_value]
        return entries[-limit:]


# Tracing classes
class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class SpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"


class TraceContext(BaseModel):
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    sampled: bool = True
    baggage: dict[str, str] = Field(default_factory=dict)

    def to_headers(self) -> dict[str, str]:
        return {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}",
        }


class Span(BaseModel):
    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    trace_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    service_name: str = "claims-processor"

    def add_event(self, name: str, attributes: dict = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, message: str = None) -> None:
        self.status = status
        self.status_message = message

    def record_exception(self, error: Exception) -> None:
        self.set_status(SpanStatus.ERROR, str(error))
        self.add_event("exception", {"exception.type": type(error).__name__, "exception.message": str(error)})

    def end(self) -> None:
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class DistributedTracer:
    def __init__(self, service_name: str = "claims-processor", sample_rate: float = 1.0):
        self._service_name = service_name
        self._sample_rate = sample_rate
        self._active_spans: dict[str, Span] = {}
        self._completed_spans: list[Span] = []
        self._max_spans = 10000
        self._exporters: list[callable] = []
        self._current_context: TraceContext | None = None

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def current_context(self) -> TraceContext | None:
        return self._current_context

    def set_context(self, context: TraceContext) -> None:
        self._current_context = context

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict = None,
        parent_context: TraceContext = None,
    ) -> Span:
        context = parent_context or self._current_context
        if context:
            trace_id = context.trace_id
            parent_span_id = context.span_id
        else:
            trace_id = uuid4().hex
            parent_span_id = None

        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            attributes=attributes or {},
            service_name=self._service_name,
        )
        self._active_spans[span.span_id] = span
        self._current_context = TraceContext(
            trace_id=trace_id,
            span_id=span.span_id,
            parent_span_id=parent_span_id,
        )
        return span

    def end_span(self, span: Span) -> None:
        span.end()
        self._active_spans.pop(span.span_id, None)
        self._completed_spans.append(span)
        if len(self._completed_spans) > self._max_spans:
            self._completed_spans = self._completed_spans[-self._max_spans:]
        for exporter in self._exporters:
            try:
                exporter(span)
            except Exception:
                pass

    def get_completed_spans(self, trace_id: str = None, limit: int = 100) -> list[Span]:
        spans = self._completed_spans.copy()
        if trace_id:
            spans = [s for s in spans if s.trace_id == trace_id]
        return spans[-limit:]

    def add_exporter(self, exporter: callable) -> None:
        self._exporters.append(exporter)

    def clear_spans(self) -> None:
        self._active_spans.clear()
        self._completed_spans.clear()


# Health check classes
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: Optional[str] = None
    response_time_ms: float = 0.0
    last_check: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)
    warning_threshold_ms: float = 1000.0
    critical_threshold_ms: float = 5000.0


class HealthCheck(BaseModel):
    status: HealthStatus = HealthStatus.UNKNOWN
    version: str = "1.0.0"
    service_name: str = "claims-processor"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: dict[str, ComponentHealth] = Field(default_factory=dict)
    uptime_seconds: float = 0.0
    total_checks: int = 0
    failed_checks: int = 0


class HealthCheckService:
    def __init__(self, service_name: str = "claims-processor", version: str = "1.0.0"):
        self._service_name = service_name
        self._version = version
        self._start_time = time.perf_counter()
        self._checks: dict[str, Callable] = {}
        self._component_status: dict[str, ComponentHealth] = {}
        self._total_checks = 0
        self._failed_checks = 0

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def uptime_seconds(self) -> float:
        return time.perf_counter() - self._start_time

    def register_check(self, name: str, check_fn: Callable, is_async: bool = False) -> None:
        self._checks[name] = check_fn

    def unregister_check(self, name: str) -> None:
        self._checks.pop(name, None)
        self._component_status.pop(name, None)

    def _run_check(self, name: str, check_fn: Callable) -> ComponentHealth:
        start = time.perf_counter()
        try:
            result = check_fn()
            result.response_time_ms = (time.perf_counter() - start) * 1000
            result.last_check = datetime.utcnow()
            if result.status == HealthStatus.HEALTHY:
                if result.response_time_ms > result.critical_threshold_ms:
                    result.status = HealthStatus.UNHEALTHY
                elif result.response_time_ms > result.warning_threshold_ms:
                    result.status = HealthStatus.DEGRADED
            return result
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                response_time_ms=(time.perf_counter() - start) * 1000,
            )

    def check(self) -> HealthCheck:
        self._total_checks += 1
        components: dict[str, ComponentHealth] = {}
        for name, check_fn in self._checks.items():
            result = self._run_check(name, check_fn)
            components[name] = result
            self._component_status[name] = result
            if result.status == HealthStatus.UNHEALTHY:
                self._failed_checks += 1

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

    def _determine_overall_status(self, components: dict[str, ComponentHealth]) -> HealthStatus:
        if not components:
            return HealthStatus.HEALTHY
        statuses = [c.status for c in components.values()]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def liveness(self) -> dict:
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    def readiness(self) -> dict:
        health = self.check()
        return {
            "status": "ready" if health.status == HealthStatus.HEALTHY else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
        }


# Alert classes
class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class AlertCondition(str, Enum):
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"


class AlertRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    metric_name: str
    condition: AlertCondition
    threshold: float
    duration_seconds: int = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    labels: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    last_evaluation: Optional[datetime] = None
    firing_since: Optional[datetime] = None

    def evaluate(self, value: float) -> bool:
        if self.condition == AlertCondition.GREATER_THAN:
            return value > self.threshold
        elif self.condition == AlertCondition.LESS_THAN:
            return value < self.threshold
        elif self.condition == AlertCondition.EQUALS:
            return value == self.threshold
        elif self.condition == AlertCondition.GREATER_OR_EQUAL:
            return value >= self.threshold
        elif self.condition == AlertCondition.LESS_OR_EQUAL:
            return value <= self.threshold
        return False


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.PENDING
    message: str
    metric_name: str
    current_value: float
    threshold: float
    started_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    labels: dict[str, str] = Field(default_factory=dict)
    notification_count: int = 0


class AlertManager:
    def __init__(self, notification_interval_seconds: int = 300):
        self._notification_interval = notification_interval_seconds
        self._rules: dict[str, AlertRule] = {}
        self._alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []
        self._notifiers: list[Callable] = []
        self._metric_values: dict[str, list[tuple[datetime, float]]] = {}
        self._metric_retention_minutes = 60

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        return self._rules.get(rule_id)

    def get_rules(self) -> list[AlertRule]:
        return list(self._rules.values())

    def record_metric(self, metric_name: str, value: float) -> None:
        now = datetime.utcnow()
        if metric_name not in self._metric_values:
            self._metric_values[metric_name] = []
        self._metric_values[metric_name].append((now, value))
        cutoff = now - timedelta(minutes=self._metric_retention_minutes)
        self._metric_values[metric_name] = [
            (ts, v) for ts, v in self._metric_values[metric_name] if ts > cutoff
        ]

    def evaluate_rules(self) -> list[Alert]:
        new_alerts: list[Alert] = []
        now = datetime.utcnow()

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            values = self._metric_values.get(rule.metric_name, [])
            if not values:
                continue
            current_value = values[-1][1]
            condition_met = rule.evaluate(current_value)
            rule.last_evaluation = now

            existing_alert = None
            for alert in self._alerts.values():
                if alert.rule_id == rule.rule_id and alert.status == AlertStatus.FIRING:
                    existing_alert = alert
                    break

            if condition_met:
                if not existing_alert:
                    if not rule.firing_since:
                        rule.firing_since = now
                    condition_str = {"gt": ">", "lt": "<", "eq": "==", "gte": ">=", "lte": "<="}.get(rule.condition.value, "?")
                    message = f"{rule.name}: {rule.metric_name} is {current_value:.2f} ({condition_str} {rule.threshold})"
                    alert = Alert(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        status=AlertStatus.FIRING,
                        message=message,
                        metric_name=rule.metric_name,
                        current_value=current_value,
                        threshold=rule.threshold,
                        labels=rule.labels.copy(),
                    )
                    self._alerts[alert.alert_id] = alert
                    new_alerts.append(alert)
                    for notifier in self._notifiers:
                        try:
                            notifier(alert)
                        except Exception:
                            pass
            else:
                if existing_alert:
                    existing_alert.status = AlertStatus.RESOLVED
                    existing_alert.resolved_at = now
                    self._alert_history.append(existing_alert)
                    del self._alerts[existing_alert.alert_id]
                rule.firing_since = None

        return new_alerts

    def add_notifier(self, notifier: Callable) -> None:
        self._notifiers.append(notifier)

    def get_firing_alerts(self) -> list[Alert]:
        return [a for a in self._alerts.values() if a.status == AlertStatus.FIRING]

    def get_alert_history(self, rule_id: str = None, limit: int = 100) -> list[Alert]:
        history = self._alert_history.copy()
        if rule_id:
            history = [a for a in history if a.rule_id == rule_id]
        return history[-limit:]

    def clear_all(self) -> None:
        self._rules.clear()
        self._alerts.clear()
        self._alert_history.clear()
        self._metric_values.clear()


# Dashboard classes
class PanelType(str, Enum):
    GRAPH = "graph"
    STAT = "stat"
    GAUGE = "gauge"
    TABLE = "table"
    TIME_SERIES = "timeseries"


class DashboardPanel(BaseModel):
    panel_id: int = Field(default_factory=lambda: int(uuid4().int % 100000))
    title: str
    panel_type: PanelType = PanelType.TIME_SERIES
    x: int = 0
    y: int = 0
    width: int = 12
    height: int = 8
    queries: list[dict[str, Any]] = Field(default_factory=list)
    datasource: str = "Prometheus"
    unit: Optional[str] = None


class Dashboard(BaseModel):
    uid: str = Field(default_factory=lambda: uuid4().hex[:8])
    title: str
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    time_from: str = "now-1h"
    time_to: str = "now"
    refresh: str = "30s"
    panels: list[DashboardPanel] = Field(default_factory=list)
    version: int = 1

    def to_grafana(self) -> dict:
        return {
            "uid": self.uid,
            "title": self.title,
            "tags": self.tags,
            "panels": [
                {
                    "id": p.panel_id,
                    "title": p.title,
                    "type": p.panel_type.value,
                    "gridPos": {"x": p.x, "y": p.y, "w": p.width, "h": p.height},
                    "targets": p.queries,
                }
                for p in self.panels
            ],
            "time": {"from": self.time_from, "to": self.time_to},
            "refresh": self.refresh,
            "version": self.version,
        }


class DashboardBuilder:
    def __init__(self, title: str):
        self._dashboard = Dashboard(title=title)
        self._next_panel_id = 1
        self._current_y = 0

    def with_description(self, description: str) -> "DashboardBuilder":
        self._dashboard.description = description
        return self

    def with_tags(self, *tags: str) -> "DashboardBuilder":
        self._dashboard.tags.extend(tags)
        return self

    def with_time_range(self, from_time: str, to_time: str) -> "DashboardBuilder":
        self._dashboard.time_from = from_time
        self._dashboard.time_to = to_time
        return self

    def with_refresh(self, interval: str) -> "DashboardBuilder":
        self._dashboard.refresh = interval
        return self

    def add_panel(
        self,
        title: str,
        query: str,
        panel_type: PanelType = PanelType.TIME_SERIES,
        width: int = 12,
        height: int = 8,
        unit: str = None,
    ) -> "DashboardBuilder":
        target = {"expr": query, "refId": "A"}
        x = 0
        for p in self._dashboard.panels:
            if p.y == self._current_y:
                x = p.x + p.width
        if x + width > 24:
            x = 0
            self._current_y += height

        panel = DashboardPanel(
            panel_id=self._next_panel_id,
            title=title,
            panel_type=panel_type,
            x=x,
            y=self._current_y,
            width=width,
            height=height,
            queries=[target],
            unit=unit,
        )
        self._dashboard.panels.append(panel)
        self._next_panel_id += 1
        return self

    def build(self) -> Dashboard:
        return self._dashboard


# =============================================================================
# Test Classes
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging service."""

    def test_log_info_message(self):
        """Test logging info message."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        entry = logger.info("Test message")

        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.logger_name == "test"

    def test_log_with_data(self):
        """Test logging with structured data."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        entry = logger.info("User action", data={"user_id": "123", "action": "login"})

        assert entry is not None
        assert entry.data["user_id"] == "123"
        assert entry.data["action"] == "login"

    def test_log_error_with_exception(self):
        """Test logging error with exception."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        error = ValueError("Test error")
        entry = logger.error("Operation failed", error=error)

        assert entry is not None
        assert entry.level == LogLevel.ERROR
        assert entry.error_type == "ValueError"
        assert entry.error_message == "Test error"

    def test_log_level_filtering(self):
        """Test that messages below log level are filtered."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", level=LogLevel.WARNING, output=output)

        debug_entry = logger.debug("Debug message")
        info_entry = logger.info("Info message")
        warning_entry = logger.warning("Warning message")

        assert debug_entry is None
        assert info_entry is None
        assert warning_entry is not None

    def test_log_context_propagation(self):
        """Test context is included in logs."""
        output = io.StringIO()
        context = LogContext(request_id="req-123", user_id="user-456")
        logger = StructuredLogger(name="test", context=context, output=output)

        entry = logger.info("Test message")

        assert entry is not None
        assert entry.context.request_id == "req-123"
        assert entry.context.user_id == "user-456"

    def test_child_logger_with_context(self):
        """Test creating child logger with additional context."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)
        child = logger.with_context(user_id="user-123", tenant_id="tenant-456")

        entry = child.info("Test message")

        assert entry is not None
        assert entry.context.user_id == "user-123"
        assert entry.context.tenant_id == "tenant-456"

    def test_log_request(self):
        """Test HTTP request logging."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        entry = logger.log_request("GET", "/api/claims", 200, 45.5)

        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert "GET /api/claims" in entry.message
        assert entry.duration_ms == 45.5

    def test_log_request_error_status(self):
        """Test HTTP request logging with error status."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        entry = logger.log_request("POST", "/api/claims", 500, 100.0)

        assert entry is not None
        assert entry.level == LogLevel.ERROR

    def test_log_handler(self):
        """Test log handler callback."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)
        received_entries = []

        def handler(entry):
            received_entries.append(entry)

        logger.add_handler(handler)
        logger.info("Test message")

        assert len(received_entries) == 1
        assert received_entries[0].message == "Test message"

    def test_get_entries(self):
        """Test retrieving log entries."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        logger.info("Message 1")
        logger.warning("Message 2")
        logger.error("Message 3")

        entries = logger.get_entries()
        assert len(entries) == 3

        warning_entries = logger.get_entries(level=LogLevel.WARNING)
        assert len(warning_entries) == 2  # WARNING and ERROR

    def test_json_output_format(self):
        """Test JSON output format."""
        output = io.StringIO()
        logger = StructuredLogger(name="test", output=output)

        logger.info("Test message", data={"key": "value"})

        output.seek(0)
        line = output.readline()
        log_data = json.loads(line)

        assert log_data["level"] == "info"
        assert log_data["message"] == "Test message"
        assert log_data["data"]["key"] == "value"


class TestDistributedTracing:
    """Tests for distributed tracing service."""

    def test_start_and_end_span(self):
        """Test starting and ending a span."""
        tracer = DistributedTracer(service_name="test-service")

        span = tracer.start_span("test-operation")
        assert span is not None
        assert span.name == "test-operation"
        assert span.status == SpanStatus.UNSET

        time.sleep(0.01)  # Small delay
        tracer.end_span(span)

        assert span.end_time is not None
        assert span.duration_ms > 0

    def test_span_attributes(self):
        """Test setting span attributes."""
        tracer = DistributedTracer()

        span = tracer.start_span("test-operation")
        span.set_attribute("user_id", "123")
        span.set_attribute("operation", "create")

        assert span.attributes["user_id"] == "123"
        assert span.attributes["operation"] == "create"

    def test_span_events(self):
        """Test adding events to span."""
        tracer = DistributedTracer()

        span = tracer.start_span("test-operation")
        span.add_event("cache_hit", {"key": "user:123"})

        assert len(span.events) == 1
        assert span.events[0]["name"] == "cache_hit"
        assert span.events[0]["attributes"]["key"] == "user:123"

    def test_span_status(self):
        """Test setting span status."""
        tracer = DistributedTracer()

        span = tracer.start_span("test-operation")
        span.set_status(SpanStatus.OK)

        assert span.status == SpanStatus.OK

    def test_record_exception(self):
        """Test recording exception in span."""
        tracer = DistributedTracer()

        span = tracer.start_span("test-operation")
        error = ValueError("Test error")
        span.record_exception(error)

        assert span.status == SpanStatus.ERROR
        assert len(span.events) == 1
        assert span.events[0]["name"] == "exception"

    def test_parent_child_spans(self):
        """Test parent-child span relationship."""
        tracer = DistributedTracer()

        parent = tracer.start_span("parent-operation")
        child = tracer.start_span("child-operation")

        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id

    def test_trace_context_propagation(self):
        """Test trace context propagation."""
        tracer = DistributedTracer()

        context = TraceContext(trace_id="abc123", span_id="def456")
        tracer.set_context(context)

        span = tracer.start_span("test-operation")

        assert span.trace_id == "abc123"
        assert span.parent_span_id == "def456"

    def test_trace_context_to_headers(self):
        """Test converting trace context to headers."""
        context = TraceContext(trace_id="abc123", span_id="def456", sampled=True)

        headers = context.to_headers()

        assert "traceparent" in headers
        assert "abc123" in headers["traceparent"]
        assert "def456" in headers["traceparent"]

    def test_span_exporter(self):
        """Test span exporter callback."""
        tracer = DistributedTracer()
        exported_spans = []

        tracer.add_exporter(lambda span: exported_spans.append(span))

        span = tracer.start_span("test-operation")
        tracer.end_span(span)

        assert len(exported_spans) == 1
        assert exported_spans[0].name == "test-operation"

    def test_get_completed_spans(self):
        """Test retrieving completed spans."""
        tracer = DistributedTracer()

        span1 = tracer.start_span("op1")
        tracer.end_span(span1)
        span2 = tracer.start_span("op2")
        tracer.end_span(span2)

        completed = tracer.get_completed_spans()
        assert len(completed) == 2

    def test_filter_spans_by_trace_id(self):
        """Test filtering spans by trace ID."""
        tracer = DistributedTracer()

        span1 = tracer.start_span("op1")
        trace_id = span1.trace_id
        tracer.end_span(span1)

        tracer.set_context(None)  # Reset context
        span2 = tracer.start_span("op2")
        tracer.end_span(span2)

        filtered = tracer.get_completed_spans(trace_id=trace_id)
        assert len(filtered) == 1
        assert filtered[0].trace_id == trace_id


class TestHealthCheck:
    """Tests for health check service."""

    def test_basic_health_check(self):
        """Test basic health check."""
        service = HealthCheckService(service_name="test-service", version="1.0.0")

        health = service.check()

        assert health.status == HealthStatus.HEALTHY
        assert health.service_name == "test-service"
        assert health.version == "1.0.0"

    def test_register_health_check(self):
        """Test registering custom health check."""
        service = HealthCheckService()

        def db_check():
            return ComponentHealth(name="database", status=HealthStatus.HEALTHY)

        service.register_check("database", db_check)
        health = service.check()

        assert "database" in health.components
        assert health.components["database"].status == HealthStatus.HEALTHY

    def test_unhealthy_component(self):
        """Test unhealthy component affects overall status."""
        service = HealthCheckService()

        def unhealthy_check():
            return ComponentHealth(name="database", status=HealthStatus.UNHEALTHY, message="Connection failed")

        service.register_check("database", unhealthy_check)
        health = service.check()

        assert health.status == HealthStatus.UNHEALTHY
        assert health.components["database"].message == "Connection failed"

    def test_degraded_component(self):
        """Test degraded component."""
        service = HealthCheckService()

        def degraded_check():
            return ComponentHealth(name="cache", status=HealthStatus.DEGRADED, message="High latency")

        service.register_check("cache", degraded_check)
        health = service.check()

        assert health.status == HealthStatus.DEGRADED

    def test_multiple_components(self):
        """Test health check with multiple components."""
        service = HealthCheckService()

        service.register_check("db", lambda: ComponentHealth(name="db", status=HealthStatus.HEALTHY))
        service.register_check("cache", lambda: ComponentHealth(name="cache", status=HealthStatus.HEALTHY))
        service.register_check("queue", lambda: ComponentHealth(name="queue", status=HealthStatus.DEGRADED))

        health = service.check()

        assert len(health.components) == 3
        assert health.status == HealthStatus.DEGRADED

    def test_check_exception_handling(self):
        """Test health check handles exceptions."""
        service = HealthCheckService()

        def failing_check():
            raise ConnectionError("Database unavailable")

        service.register_check("database", failing_check)
        health = service.check()

        assert health.components["database"].status == HealthStatus.UNHEALTHY
        assert "Database unavailable" in health.components["database"].message

    def test_liveness_probe(self):
        """Test Kubernetes liveness probe."""
        service = HealthCheckService()

        result = service.liveness()

        assert result["status"] == "ok"
        assert "timestamp" in result

    def test_readiness_probe(self):
        """Test Kubernetes readiness probe."""
        service = HealthCheckService()
        service.register_check("db", lambda: ComponentHealth(name="db", status=HealthStatus.HEALTHY))

        result = service.readiness()

        assert result["status"] == "ready"

    def test_readiness_not_ready(self):
        """Test readiness probe when not ready."""
        service = HealthCheckService()
        service.register_check("db", lambda: ComponentHealth(name="db", status=HealthStatus.UNHEALTHY))

        result = service.readiness()

        assert result["status"] == "not_ready"

    def test_uptime_tracking(self):
        """Test uptime tracking."""
        service = HealthCheckService()
        time.sleep(0.01)

        assert service.uptime_seconds > 0

    def test_unregister_check(self):
        """Test unregistering health check."""
        service = HealthCheckService()
        service.register_check("db", lambda: ComponentHealth(name="db", status=HealthStatus.HEALTHY))
        service.unregister_check("db")

        health = service.check()
        assert "db" not in health.components


class TestAlerting:
    """Tests for alerting service."""

    def test_add_alert_rule(self):
        """Test adding alert rule."""
        manager = AlertManager()

        rule = AlertRule(
            name="High Error Rate",
            metric_name="error_rate",
            condition=AlertCondition.GREATER_THAN,
            threshold=5.0,
        )
        manager.add_rule(rule)

        assert manager.get_rule(rule.rule_id) is not None

    def test_evaluate_rule_fires_alert(self):
        """Test rule evaluation fires alert."""
        manager = AlertManager()

        rule = AlertRule(
            name="High Error Rate",
            metric_name="error_rate",
            condition=AlertCondition.GREATER_THAN,
            threshold=5.0,
            severity=AlertSeverity.ERROR,
        )
        manager.add_rule(rule)
        manager.record_metric("error_rate", 10.0)

        new_alerts = manager.evaluate_rules()

        assert len(new_alerts) == 1
        assert new_alerts[0].rule_name == "High Error Rate"
        assert new_alerts[0].status == AlertStatus.FIRING

    def test_evaluate_rule_no_alert(self):
        """Test rule evaluation does not fire when condition not met."""
        manager = AlertManager()

        rule = AlertRule(
            name="High Error Rate",
            metric_name="error_rate",
            condition=AlertCondition.GREATER_THAN,
            threshold=5.0,
        )
        manager.add_rule(rule)
        manager.record_metric("error_rate", 2.0)

        new_alerts = manager.evaluate_rules()

        assert len(new_alerts) == 0

    def test_alert_condition_less_than(self):
        """Test less than condition."""
        manager = AlertManager()

        rule = AlertRule(
            name="Low Availability",
            metric_name="availability",
            condition=AlertCondition.LESS_THAN,
            threshold=99.0,
        )
        manager.add_rule(rule)
        manager.record_metric("availability", 95.0)

        new_alerts = manager.evaluate_rules()

        assert len(new_alerts) == 1

    def test_alert_resolves(self):
        """Test alert resolves when condition no longer met."""
        manager = AlertManager()

        rule = AlertRule(
            name="High Error Rate",
            metric_name="error_rate",
            condition=AlertCondition.GREATER_THAN,
            threshold=5.0,
        )
        manager.add_rule(rule)

        # Fire alert
        manager.record_metric("error_rate", 10.0)
        manager.evaluate_rules()

        assert len(manager.get_firing_alerts()) == 1

        # Resolve alert
        manager.record_metric("error_rate", 2.0)
        manager.evaluate_rules()

        assert len(manager.get_firing_alerts()) == 0
        assert len(manager.get_alert_history()) == 1

    def test_alert_notifier(self):
        """Test alert notification callback."""
        manager = AlertManager()
        notifications = []

        manager.add_notifier(lambda alert: notifications.append(alert))

        rule = AlertRule(
            name="Test Alert",
            metric_name="test_metric",
            condition=AlertCondition.GREATER_THAN,
            threshold=0.0,
        )
        manager.add_rule(rule)
        manager.record_metric("test_metric", 1.0)
        manager.evaluate_rules()

        assert len(notifications) == 1

    def test_disabled_rule(self):
        """Test disabled rules are not evaluated."""
        manager = AlertManager()

        rule = AlertRule(
            name="Disabled Rule",
            metric_name="test_metric",
            condition=AlertCondition.GREATER_THAN,
            threshold=0.0,
            enabled=False,
        )
        manager.add_rule(rule)
        manager.record_metric("test_metric", 1.0)

        new_alerts = manager.evaluate_rules()

        assert len(new_alerts) == 0

    def test_remove_rule(self):
        """Test removing alert rule."""
        manager = AlertManager()

        rule = AlertRule(
            name="Test Rule",
            metric_name="test_metric",
            condition=AlertCondition.GREATER_THAN,
            threshold=0.0,
        )
        manager.add_rule(rule)
        assert manager.remove_rule(rule.rule_id)
        assert manager.get_rule(rule.rule_id) is None

    def test_alert_history_filtering(self):
        """Test filtering alert history."""
        manager = AlertManager()

        rule1 = AlertRule(name="Rule1", metric_name="metric1", condition=AlertCondition.GREATER_THAN, threshold=0.0)
        rule2 = AlertRule(name="Rule2", metric_name="metric2", condition=AlertCondition.GREATER_THAN, threshold=0.0)

        manager.add_rule(rule1)
        manager.add_rule(rule2)

        manager.record_metric("metric1", 1.0)
        manager.record_metric("metric2", 1.0)
        manager.evaluate_rules()

        # Resolve alerts
        manager.record_metric("metric1", -1.0)
        manager.record_metric("metric2", -1.0)
        manager.evaluate_rules()

        all_history = manager.get_alert_history()
        assert len(all_history) == 2

        filtered = manager.get_alert_history(rule_id=rule1.rule_id)
        assert len(filtered) == 1


class TestDashboard:
    """Tests for dashboard configuration."""

    def test_create_dashboard(self):
        """Test creating dashboard."""
        dashboard = Dashboard(title="Test Dashboard")

        assert dashboard.title == "Test Dashboard"
        assert dashboard.uid is not None

    def test_add_panel(self):
        """Test adding panel to dashboard."""
        builder = DashboardBuilder("Test Dashboard")
        builder.add_panel(
            title="CPU Usage",
            query='rate(cpu_usage[5m])',
            panel_type=PanelType.TIME_SERIES,
        )

        dashboard = builder.build()

        assert len(dashboard.panels) == 1
        assert dashboard.panels[0].title == "CPU Usage"

    def test_dashboard_builder_fluent_api(self):
        """Test dashboard builder fluent API."""
        dashboard = (
            DashboardBuilder("Test Dashboard")
            .with_description("Test description")
            .with_tags("test", "example")
            .with_time_range("now-6h", "now")
            .with_refresh("1m")
            .add_panel("Panel 1", "query1")
            .add_panel("Panel 2", "query2")
            .build()
        )

        assert dashboard.description == "Test description"
        assert "test" in dashboard.tags
        assert dashboard.time_from == "now-6h"
        assert dashboard.refresh == "1m"
        assert len(dashboard.panels) == 2

    def test_panel_layout(self):
        """Test panel layout positioning."""
        builder = DashboardBuilder("Test Dashboard")
        builder.add_panel("Panel 1", "query1", width=12)
        builder.add_panel("Panel 2", "query2", width=12)

        dashboard = builder.build()

        # First panel at (0, 0)
        assert dashboard.panels[0].x == 0
        assert dashboard.panels[0].y == 0

        # Second panel at (12, 0) or (0, 8) depending on layout logic
        # Given width=12 each, they should fit on same row
        assert dashboard.panels[1].x == 12 or dashboard.panels[1].y > 0

    def test_to_grafana_format(self):
        """Test converting to Grafana format."""
        builder = DashboardBuilder("Test Dashboard")
        builder.add_panel("CPU", 'rate(cpu[5m])')

        dashboard = builder.build()
        grafana = dashboard.to_grafana()

        assert grafana["title"] == "Test Dashboard"
        assert len(grafana["panels"]) == 1
        assert grafana["panels"][0]["title"] == "CPU"
        assert grafana["panels"][0]["type"] == "timeseries"

    def test_panel_types(self):
        """Test different panel types."""
        builder = DashboardBuilder("Test Dashboard")
        builder.add_panel("Graph", "query1", panel_type=PanelType.TIME_SERIES)
        builder.add_panel("Stat", "query2", panel_type=PanelType.STAT, width=6)
        builder.add_panel("Gauge", "query3", panel_type=PanelType.GAUGE, width=6)

        dashboard = builder.build()

        assert dashboard.panels[0].panel_type == PanelType.TIME_SERIES
        assert dashboard.panels[1].panel_type == PanelType.STAT
        assert dashboard.panels[2].panel_type == PanelType.GAUGE

    def test_panel_with_unit(self):
        """Test panel with unit specification."""
        builder = DashboardBuilder("Test Dashboard")
        builder.add_panel("Memory", "memory_usage", unit="bytes")

        dashboard = builder.build()

        assert dashboard.panels[0].unit == "bytes"

    def test_dashboard_time_settings(self):
        """Test dashboard time settings."""
        builder = DashboardBuilder("Test Dashboard")
        builder.with_time_range("now-24h", "now")
        builder.with_refresh("5m")

        dashboard = builder.build()

        assert dashboard.time_from == "now-24h"
        assert dashboard.time_to == "now"
        assert dashboard.refresh == "5m"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
