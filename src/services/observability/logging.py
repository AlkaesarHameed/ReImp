"""
Structured Logging Service.
Source: Design Document Section 5.3 - Monitoring & Observability
Verified: 2025-12-18

Provides structured JSON logging with context propagation.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TextIO
from uuid import uuid4

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Numeric values for level comparison
LOG_LEVEL_VALUES = {
    LogLevel.DEBUG: 10,
    LogLevel.INFO: 20,
    LogLevel.WARNING: 30,
    LogLevel.ERROR: 40,
    LogLevel.CRITICAL: 50,
}


class LogContext(BaseModel):
    """Context information for structured logging."""

    # Request context
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None

    # User context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Service context
    service_name: str = "claims-processor"
    environment: str = "development"
    version: str = "1.0.0"

    # Trace context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    # Custom fields
    extra: dict[str, Any] = Field(default_factory=dict)


class LogEntry(BaseModel):
    """Structured log entry."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    message: str
    logger_name: str = "app"

    # Context
    context: LogContext = Field(default_factory=LogContext)

    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    # Structured data
    data: dict[str, Any] = Field(default_factory=dict)

    # Performance
    duration_ms: Optional[float] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "logger": self.logger_name,
        }

        # Add context fields
        if self.context.request_id:
            result["request_id"] = self.context.request_id
        if self.context.correlation_id:
            result["correlation_id"] = self.context.correlation_id
        if self.context.user_id:
            result["user_id"] = self.context.user_id
        if self.context.tenant_id:
            result["tenant_id"] = self.context.tenant_id
        if self.context.trace_id:
            result["trace_id"] = self.context.trace_id
        if self.context.span_id:
            result["span_id"] = self.context.span_id

        result["service"] = self.context.service_name
        result["environment"] = self.context.environment

        # Add error info
        if self.error_type:
            result["error"] = {
                "type": self.error_type,
                "message": self.error_message,
            }
            if self.stack_trace:
                result["error"]["stack_trace"] = self.stack_trace

        # Add data
        if self.data:
            result["data"] = self.data

        # Add duration
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms

        # Add extra context
        if self.context.extra:
            result.update(self.context.extra)

        return result


class StructuredLogger:
    """Structured JSON logger."""

    def __init__(
        self,
        name: str = "app",
        level: LogLevel = LogLevel.INFO,
        context: LogContext | None = None,
        output: TextIO | None = None,
    ):
        """Initialize StructuredLogger.

        Args:
            name: Logger name
            level: Minimum log level
            context: Default context for all entries
            output: Output stream (default: stdout)
        """
        self._name = name
        self._level = level
        self._context = context or LogContext()
        self._output = output or sys.stdout
        self._handlers: list[callable] = []
        self._entries: list[LogEntry] = []
        self._max_entries = 10000

    @property
    def name(self) -> str:
        """Get logger name."""
        return self._name

    @property
    def level(self) -> LogLevel:
        """Get current log level."""
        return self._level

    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self._level = level

    def set_context(self, context: LogContext) -> None:
        """Set default context."""
        self._context = context

    def with_context(self, **kwargs) -> "StructuredLogger":
        """Create child logger with additional context."""
        new_context = self._context.model_copy()

        # Update context fields
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
        """Check if message should be logged."""
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
        """Internal log method."""
        if not self._should_log(level):
            return None

        # Build context with overrides
        context = self._context.model_copy()
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.extra[key] = value

        # Create entry
        entry = LogEntry(
            level=level,
            message=message,
            logger_name=self._name,
            context=context,
            data=data or {},
            duration_ms=duration_ms,
        )

        # Add error info
        if error:
            entry.error_type = type(error).__name__
            entry.error_message = str(error)
            import traceback

            entry.stack_trace = traceback.format_exc()

        # Store entry
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

        # Output
        self._write(entry)

        # Notify handlers
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception:
                pass  # Don't let handler errors affect logging

        return entry

    def _write(self, entry: LogEntry) -> None:
        """Write log entry to output."""
        try:
            line = json.dumps(entry.to_dict())
            self._output.write(line + "\n")
            self._output.flush()
        except Exception:
            pass  # Don't fail on write errors

    def debug(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log debug message."""
        return self._log(LogLevel.DEBUG, message, data, **kwargs)

    def info(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log info message."""
        return self._log(LogLevel.INFO, message, data, **kwargs)

    def warning(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log warning message."""
        return self._log(LogLevel.WARNING, message, data, **kwargs)

    def error(
        self,
        message: str,
        error: Exception | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log error message."""
        return self._log(LogLevel.ERROR, message, data, error=error, **kwargs)

    def critical(
        self,
        message: str,
        error: Exception | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log critical message."""
        return self._log(LogLevel.CRITICAL, message, data, error=error, **kwargs)

    def exception(
        self,
        message: str,
        error: Exception,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log exception with stack trace."""
        return self._log(LogLevel.ERROR, message, data, error=error, **kwargs)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **kwargs,
    ) -> LogEntry | None:
        """Log HTTP request."""
        level = LogLevel.INFO if status_code < 400 else LogLevel.ERROR

        return self._log(
            level,
            f"{method} {path} - {status_code}",
            data={
                "http.method": method,
                "http.path": path,
                "http.status_code": status_code,
            },
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_event(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> LogEntry | None:
        """Log application event."""
        return self._log(
            LogLevel.INFO,
            f"Event: {event_type}",
            data={"event_type": event_type, **(data or {})},
            **kwargs,
        )

    def add_handler(self, handler: callable) -> None:
        """Add log entry handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: callable) -> None:
        """Remove log entry handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def get_entries(
        self,
        level: LogLevel | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get recent log entries."""
        entries = self._entries.copy()

        if level:
            min_value = LOG_LEVEL_VALUES[level]
            entries = [
                e for e in entries if LOG_LEVEL_VALUES[e.level] >= min_value
            ]

        return entries[-limit:]

    def clear_entries(self) -> None:
        """Clear stored entries."""
        self._entries.clear()


# =============================================================================
# Factory Functions
# =============================================================================


_logger: StructuredLogger | None = None


def get_logger(name: str = "app") -> StructuredLogger:
    """Get singleton logger instance."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name=name)
    return _logger


def create_logger(
    name: str = "app",
    level: LogLevel = LogLevel.INFO,
    context: LogContext | None = None,
) -> StructuredLogger:
    """Create new logger instance."""
    return StructuredLogger(name=name, level=level, context=context)
