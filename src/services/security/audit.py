"""
Security Audit Service.
Source: Design Document Section 5.2 - Security Hardening
Verified: 2025-12-18

Provides security event auditing and compliance logging.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of security audit events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_CHALLENGE = "mfa_challenge"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    ROLE_ASSIGNMENT = "role_assignment"

    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    PHI_ACCESS = "phi_access"

    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_TOKEN = "invalid_token"
    INJECTION_ATTEMPT = "injection_attempt"
    BRUTE_FORCE_DETECTED = "brute_force_detected"

    # System events
    CONFIG_CHANGE = "config_change"
    SECRET_ACCESS = "secret_access"
    KEY_ROTATION = "key_rotation"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Security audit event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Actor information
    user_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Resource information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None

    # Event details
    success: bool = True
    message: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    # Request context
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None

    # Compliance tags
    compliance_tags: list[str] = Field(default_factory=list)


class AuditQuery(BaseModel):
    """Query parameters for audit log search."""

    event_types: Optional[list[AuditEventType]] = None
    severity: Optional[list[AuditSeverity]] = None
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    ip_address: Optional[str] = None
    limit: int = 100
    offset: int = 0


class AuditSummary(BaseModel):
    """Summary of audit events."""

    total_events: int = 0
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_severity: dict[str, int] = Field(default_factory=dict)
    failed_events: int = 0
    unique_users: int = 0
    unique_ips: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class SecurityAuditService:
    """Security audit logging service."""

    def __init__(self, max_events: int = 100000):
        """Initialize SecurityAuditService.

        Args:
            max_events: Maximum events to keep in memory
        """
        self._max_events = max_events
        self._events: list[AuditEvent] = []
        self._event_handlers: list[callable] = []

    def log(
        self,
        event_type: AuditEventType,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        success: bool = True,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        severity: AuditSeverity | None = None,
        ip_address: str | None = None,
        **kwargs,
    ) -> AuditEvent:
        """Log a security audit event.

        Args:
            event_type: Type of event
            user_id: ID of the user
            resource_type: Type of resource accessed
            resource_id: ID of the resource
            success: Whether the action was successful
            message: Human-readable message
            details: Additional details
            severity: Event severity (auto-determined if not provided)
            ip_address: Client IP address
            **kwargs: Additional event fields

        Returns:
            Created audit event
        """
        # Auto-determine severity if not provided
        if severity is None:
            severity = self._determine_severity(event_type, success)

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            message=message,
            details=details or {},
            ip_address=ip_address,
            **kwargs,
        )

        # Add compliance tags based on event type
        event.compliance_tags = self._get_compliance_tags(event_type)

        # Store event
        self._events.append(event)

        # Trim if exceeding max
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        # Notify handlers
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors affect logging

        return event

    def _determine_severity(self, event_type: AuditEventType, success: bool) -> AuditSeverity:
        """Determine severity based on event type and success."""
        critical_types = {
            AuditEventType.BRUTE_FORCE_DETECTED,
            AuditEventType.INJECTION_ATTEMPT,
        }

        error_types = {
            AuditEventType.ACCESS_DENIED,
            AuditEventType.INVALID_TOKEN,
            AuditEventType.RATE_LIMIT_EXCEEDED,
        }

        warning_types = {
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.PASSWORD_RESET,
        }

        if event_type in critical_types:
            return AuditSeverity.CRITICAL

        if event_type in error_types or not success:
            return AuditSeverity.ERROR

        if event_type in warning_types:
            return AuditSeverity.WARNING

        return AuditSeverity.INFO

    def _get_compliance_tags(self, event_type: AuditEventType) -> list[str]:
        """Get compliance tags for event type."""
        tags = []

        # HIPAA tags
        hipaa_types = {
            AuditEventType.PHI_ACCESS,
            AuditEventType.DATA_READ,
            AuditEventType.DATA_CREATE,
            AuditEventType.DATA_UPDATE,
            AuditEventType.DATA_DELETE,
            AuditEventType.DATA_EXPORT,
            AuditEventType.LOGIN_SUCCESS,
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.ACCESS_DENIED,
        }
        if event_type in hipaa_types:
            tags.append("HIPAA")

        # SOC2 tags
        soc2_types = {
            AuditEventType.ACCESS_GRANTED,
            AuditEventType.ACCESS_DENIED,
            AuditEventType.CONFIG_CHANGE,
            AuditEventType.PERMISSION_CHANGE,
            AuditEventType.KEY_ROTATION,
        }
        if event_type in soc2_types:
            tags.append("SOC2")

        return tags

    def query(self, query: AuditQuery) -> list[AuditEvent]:
        """Query audit events.

        Args:
            query: Query parameters

        Returns:
            List of matching events
        """
        results = self._events.copy()

        # Filter by event types
        if query.event_types:
            results = [e for e in results if e.event_type in query.event_types]

        # Filter by severity
        if query.severity:
            results = [e for e in results if e.severity in query.severity]

        # Filter by user
        if query.user_id:
            results = [e for e in results if e.user_id == query.user_id]

        # Filter by resource
        if query.resource_type:
            results = [e for e in results if e.resource_type == query.resource_type]

        if query.resource_id:
            results = [e for e in results if e.resource_id == query.resource_id]

        # Filter by time range
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]

        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]

        # Filter by success
        if query.success is not None:
            results = [e for e in results if e.success == query.success]

        # Filter by IP
        if query.ip_address:
            results = [e for e in results if e.ip_address == query.ip_address]

        # Apply pagination
        return results[query.offset : query.offset + query.limit]

    def get_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AuditSummary:
        """Get summary of audit events.

        Args:
            start_time: Start of period
            end_time: End of period

        Returns:
            AuditSummary
        """
        events = self._events.copy()

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        events_by_type: dict[str, int] = {}
        events_by_severity: dict[str, int] = {}
        users = set()
        ips = set()
        failed = 0

        for event in events:
            # Count by type
            type_key = event.event_type.value
            events_by_type[type_key] = events_by_type.get(type_key, 0) + 1

            # Count by severity
            sev_key = event.severity.value
            events_by_severity[sev_key] = events_by_severity.get(sev_key, 0) + 1

            # Track unique users and IPs
            if event.user_id:
                users.add(event.user_id)
            if event.ip_address:
                ips.add(event.ip_address)

            # Count failures
            if not event.success:
                failed += 1

        return AuditSummary(
            total_events=len(events),
            events_by_type=events_by_type,
            events_by_severity=events_by_severity,
            failed_events=failed,
            unique_users=len(users),
            unique_ips=len(ips),
            period_start=start_time,
            period_end=end_time,
        )

    def get_failed_logins(
        self,
        ip_address: str | None = None,
        user_id: str | None = None,
        minutes: int = 15,
    ) -> list[AuditEvent]:
        """Get recent failed login attempts.

        Args:
            ip_address: Filter by IP
            user_id: Filter by user
            minutes: Time window in minutes

        Returns:
            List of failed login events
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)

        results = [
            e for e in self._events
            if e.event_type == AuditEventType.LOGIN_FAILURE
            and e.timestamp >= cutoff
        ]

        if ip_address:
            results = [e for e in results if e.ip_address == ip_address]

        if user_id:
            results = [e for e in results if e.user_id == user_id]

        return results

    def detect_brute_force(
        self,
        ip_address: str,
        threshold: int = 5,
        minutes: int = 15,
    ) -> bool:
        """Detect potential brute force attack.

        Args:
            ip_address: IP to check
            threshold: Number of failed attempts to trigger
            minutes: Time window

        Returns:
            True if brute force detected
        """
        failed_attempts = self.get_failed_logins(ip_address=ip_address, minutes=minutes)

        if len(failed_attempts) >= threshold:
            # Log the detection
            self.log(
                AuditEventType.BRUTE_FORCE_DETECTED,
                ip_address=ip_address,
                message=f"Brute force detected: {len(failed_attempts)} failed attempts in {minutes} minutes",
                details={"attempt_count": len(failed_attempts), "window_minutes": minutes},
            )
            return True

        return False

    def add_handler(self, handler: callable) -> None:
        """Add event handler for real-time processing.

        Args:
            handler: Callable that receives AuditEvent
        """
        self._event_handlers.append(handler)

    def remove_handler(self, handler: callable) -> None:
        """Remove event handler."""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def export_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        format: str = "json",
    ) -> list[dict]:
        """Export events for compliance reporting.

        Args:
            start_time: Start of period
            end_time: End of period
            format: Export format (json)

        Returns:
            List of event dictionaries
        """
        events = self._events.copy()

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return [e.model_dump(mode="json") for e in events]

    def clear_events(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()


# =============================================================================
# Convenience logging functions
# =============================================================================


def log_login_success(
    audit: SecurityAuditService,
    user_id: str,
    ip_address: str | None = None,
    **kwargs,
) -> AuditEvent:
    """Log successful login."""
    return audit.log(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user_id,
        ip_address=ip_address,
        message="User logged in successfully",
        **kwargs,
    )


def log_login_failure(
    audit: SecurityAuditService,
    username: str,
    ip_address: str | None = None,
    reason: str = "Invalid credentials",
    **kwargs,
) -> AuditEvent:
    """Log failed login attempt."""
    return audit.log(
        AuditEventType.LOGIN_FAILURE,
        username=username,
        ip_address=ip_address,
        success=False,
        message=f"Login failed: {reason}",
        **kwargs,
    )


def log_phi_access(
    audit: SecurityAuditService,
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str = "read",
    **kwargs,
) -> AuditEvent:
    """Log PHI access."""
    return audit.log(
        AuditEventType.PHI_ACCESS,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        message=f"PHI {action}: {resource_type}/{resource_id}",
        **kwargs,
    )


# =============================================================================
# Factory Functions
# =============================================================================


_audit_service: SecurityAuditService | None = None


def get_audit_service(max_events: int = 100000) -> SecurityAuditService:
    """Get singleton SecurityAuditService instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = SecurityAuditService(max_events)
    return _audit_service


def create_audit_service(max_events: int = 100000) -> SecurityAuditService:
    """Create new SecurityAuditService instance."""
    return SecurityAuditService(max_events)
