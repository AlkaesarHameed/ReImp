"""
Distributed Tracing Service.
Source: Design Document Section 5.3 - Monitoring & Observability
Verified: 2025-12-18

Provides distributed tracing with span management.
"""

import time
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SpanStatus(str, Enum):
    """Span status codes."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class SpanKind(str, Enum):
    """Span kind for categorization."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class TraceContext(BaseModel):
    """Trace context for propagation."""

    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    sampled: bool = True

    # Baggage items for cross-service propagation
    baggage: dict[str, str] = Field(default_factory=dict)

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers for propagation."""
        headers = {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}",
        }

        if self.baggage:
            baggage_str = ",".join(f"{k}={v}" for k, v in self.baggage.items())
            headers["baggage"] = baggage_str

        return headers

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "TraceContext":
        """Parse from HTTP headers."""
        traceparent = headers.get("traceparent", "")

        if traceparent:
            parts = traceparent.split("-")
            if len(parts) == 4:
                return cls(
                    trace_id=parts[1],
                    parent_span_id=parts[2],
                    sampled=parts[3] == "01",
                )

        return cls()


class Span(BaseModel):
    """Distributed trace span."""

    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    trace_id: str
    parent_span_id: Optional[str] = None

    name: str
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: Optional[str] = None

    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0

    # Attributes
    attributes: dict[str, Any] = Field(default_factory=dict)

    # Events within span
    events: list[dict[str, Any]] = Field(default_factory=list)

    # Links to other spans
    links: list[str] = Field(default_factory=list)

    # Service info
    service_name: str = "claims-processor"
    service_version: str = "1.0.0"

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add event to span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, message: str | None = None) -> None:
        """Set span status."""
        self.status = status
        self.status_message = message

    def record_exception(self, error: Exception) -> None:
        """Record exception in span."""
        self.set_status(SpanStatus.ERROR, str(error))
        self.add_event(
            "exception",
            {
                "exception.type": type(error).__name__,
                "exception.message": str(error),
            },
        )

    def end(self) -> None:
        """End the span."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (
            self.end_time - self.start_time
        ).total_seconds() * 1000

    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "statusMessage": self.status_message,
            "startTime": self.start_time.isoformat(),
            "endTime": self.end_time.isoformat() if self.end_time else None,
            "durationMs": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "links": self.links,
            "service": {
                "name": self.service_name,
                "version": self.service_version,
            },
        }


class DistributedTracer:
    """Distributed tracing service."""

    def __init__(
        self,
        service_name: str = "claims-processor",
        service_version: str = "1.0.0",
        sample_rate: float = 1.0,
    ):
        """Initialize tracer.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            sample_rate: Sampling rate (0.0 to 1.0)
        """
        self._service_name = service_name
        self._service_version = service_version
        self._sample_rate = sample_rate

        self._active_spans: dict[str, Span] = {}
        self._completed_spans: list[Span] = []
        self._max_spans = 10000

        self._exporters: list[callable] = []

        # Current context (per-request in real implementation)
        self._current_context: TraceContext | None = None

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def current_context(self) -> TraceContext | None:
        """Get current trace context."""
        return self._current_context

    def set_context(self, context: TraceContext) -> None:
        """Set current trace context."""
        self._current_context = context

    def _should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        import random

        return random.random() < self._sample_rate

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
        parent_context: TraceContext | None = None,
    ) -> Span:
        """Start a new span.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes
            parent_context: Parent trace context

        Returns:
            New span
        """
        # Determine trace ID and parent
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
            service_version=self._service_version,
        )

        self._active_spans[span.span_id] = span

        # Update current context
        self._current_context = TraceContext(
            trace_id=trace_id,
            span_id=span.span_id,
            parent_span_id=parent_span_id,
        )

        return span

    def end_span(self, span: Span) -> None:
        """End a span.

        Args:
            span: Span to end
        """
        span.end()

        # Remove from active
        self._active_spans.pop(span.span_id, None)

        # Add to completed
        self._completed_spans.append(span)
        if len(self._completed_spans) > self._max_spans:
            self._completed_spans = self._completed_spans[-self._max_spans :]

        # Export
        for exporter in self._exporters:
            try:
                exporter(span)
            except Exception:
                pass

        # Restore parent context
        if span.parent_span_id and span.parent_span_id in self._active_spans:
            parent = self._active_spans[span.parent_span_id]
            self._current_context = TraceContext(
                trace_id=span.trace_id,
                span_id=parent.span_id,
                parent_span_id=parent.parent_span_id,
            )

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ):
        """Context manager for spans.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes

        Yields:
            Active span
        """
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            self.end_span(span)

    def get_span(self, span_id: str) -> Span | None:
        """Get span by ID."""
        return self._active_spans.get(span_id)

    def get_active_spans(self) -> list[Span]:
        """Get all active spans."""
        return list(self._active_spans.values())

    def get_completed_spans(
        self,
        trace_id: str | None = None,
        limit: int = 100,
    ) -> list[Span]:
        """Get completed spans.

        Args:
            trace_id: Filter by trace ID
            limit: Maximum spans to return

        Returns:
            List of completed spans
        """
        spans = self._completed_spans.copy()

        if trace_id:
            spans = [s for s in spans if s.trace_id == trace_id]

        return spans[-limit:]

    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace.

        Args:
            trace_id: Trace ID

        Returns:
            All spans in the trace
        """
        active = [s for s in self._active_spans.values() if s.trace_id == trace_id]
        completed = [s for s in self._completed_spans if s.trace_id == trace_id]
        return active + completed

    def add_exporter(self, exporter: callable) -> None:
        """Add span exporter.

        Args:
            exporter: Callable that receives completed spans
        """
        self._exporters.append(exporter)

    def remove_exporter(self, exporter: callable) -> None:
        """Remove span exporter."""
        if exporter in self._exporters:
            self._exporters.remove(exporter)

    def clear_spans(self) -> None:
        """Clear all spans."""
        self._active_spans.clear()
        self._completed_spans.clear()

    def export_jaeger(self, span: Span) -> dict:
        """Export span in Jaeger format."""
        return {
            "traceID": span.trace_id,
            "spanID": span.span_id,
            "operationName": span.name,
            "references": (
                [{"refType": "CHILD_OF", "traceID": span.trace_id, "spanID": span.parent_span_id}]
                if span.parent_span_id
                else []
            ),
            "startTime": int(span.start_time.timestamp() * 1_000_000),
            "duration": int(span.duration_ms * 1000),
            "tags": [{"key": k, "type": "string", "value": str(v)} for k, v in span.attributes.items()],
            "logs": [
                {
                    "timestamp": e.get("timestamp"),
                    "fields": [{"key": k, "value": v} for k, v in e.get("attributes", {}).items()],
                }
                for e in span.events
            ],
            "processID": "p1",
            "process": {
                "serviceName": span.service_name,
                "tags": [{"key": "version", "value": span.service_version}],
            },
        }


# =============================================================================
# Convenience Functions
# =============================================================================


def trace_function(tracer: DistributedTracer, name: str | None = None):
    """Decorator for tracing functions.

    Args:
        tracer: Tracer instance
        name: Span name (defaults to function name)
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                return func(*args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Factory Functions
# =============================================================================


_tracer: DistributedTracer | None = None


def get_tracer(service_name: str = "claims-processor") -> DistributedTracer:
    """Get singleton tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = DistributedTracer(service_name=service_name)
    return _tracer


def create_tracer(
    service_name: str = "claims-processor",
    service_version: str = "1.0.0",
    sample_rate: float = 1.0,
) -> DistributedTracer:
    """Create new tracer instance."""
    return DistributedTracer(
        service_name=service_name,
        service_version=service_version,
        sample_rate=sample_rate,
    )
