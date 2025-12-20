"""
Alerting Service.
Source: Design Document Section 5.3 - Monitoring & Observability
Verified: 2025-12-18

Provides alerting rules and notification management.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""

    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class AlertCondition(str, Enum):
    """Alert condition types."""

    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"


class AlertRule(BaseModel):
    """Alert rule definition."""

    rule_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None

    # Condition
    metric_name: str
    condition: AlertCondition
    threshold: float

    # Timing
    duration_seconds: int = 0  # How long condition must be true
    evaluation_interval_seconds: int = 60

    # Severity and labeling
    severity: AlertSeverity = AlertSeverity.WARNING
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    # State
    enabled: bool = True
    last_evaluation: Optional[datetime] = None
    firing_since: Optional[datetime] = None

    def evaluate(self, value: float) -> bool:
        """Evaluate if condition is met.

        Args:
            value: Current metric value

        Returns:
            True if condition is met
        """
        if self.condition == AlertCondition.GREATER_THAN:
            return value > self.threshold
        elif self.condition == AlertCondition.LESS_THAN:
            return value < self.threshold
        elif self.condition == AlertCondition.EQUALS:
            return value == self.threshold
        elif self.condition == AlertCondition.NOT_EQUALS:
            return value != self.threshold
        elif self.condition == AlertCondition.GREATER_OR_EQUAL:
            return value >= self.threshold
        elif self.condition == AlertCondition.LESS_OR_EQUAL:
            return value <= self.threshold
        return False


class Alert(BaseModel):
    """Alert instance."""

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    rule_name: str
    severity: AlertSeverity

    status: AlertStatus = AlertStatus.PENDING
    message: str

    # Values
    metric_name: str
    current_value: float
    threshold: float

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    last_notified_at: Optional[datetime] = None

    # Labels
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    # Notification tracking
    notification_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "started_at": self.started_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "labels": self.labels,
        }


class SilenceRule(BaseModel):
    """Alert silence rule."""

    silence_id: str = Field(default_factory=lambda: str(uuid4()))
    matchers: dict[str, str] = Field(default_factory=dict)  # Label matchers
    starts_at: datetime = Field(default_factory=datetime.utcnow)
    ends_at: datetime
    created_by: str
    comment: Optional[str] = None


class AlertManager:
    """Alert management service."""

    def __init__(
        self,
        notification_interval_seconds: int = 300,
    ):
        """Initialize alert manager.

        Args:
            notification_interval_seconds: Minimum time between notifications
        """
        self._notification_interval = notification_interval_seconds

        # Rules and alerts
        self._rules: dict[str, AlertRule] = {}
        self._alerts: dict[str, Alert] = {}
        self._silences: list[SilenceRule] = []

        # History
        self._alert_history: list[Alert] = []
        self._max_history = 10000

        # Notification channels
        self._notifiers: list[Callable[[Alert], None]] = []

        # Metric value store for evaluation
        self._metric_values: dict[str, list[tuple[datetime, float]]] = {}
        self._metric_retention_minutes = 60

    def add_rule(self, rule: AlertRule) -> None:
        """Add alert rule.

        Args:
            rule: Alert rule to add
        """
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove alert rule.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Get alert rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Alert rule or None
        """
        return self._rules.get(rule_id)

    def get_rules(self) -> list[AlertRule]:
        """Get all alert rules.

        Returns:
            List of alert rules
        """
        return list(self._rules.values())

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record metric value for alerting.

        Args:
            metric_name: Metric name
            value: Metric value
        """
        now = datetime.utcnow()

        if metric_name not in self._metric_values:
            self._metric_values[metric_name] = []

        self._metric_values[metric_name].append((now, value))

        # Cleanup old values
        cutoff = now - timedelta(minutes=self._metric_retention_minutes)
        self._metric_values[metric_name] = [
            (ts, v) for ts, v in self._metric_values[metric_name] if ts > cutoff
        ]

    def evaluate_rules(self) -> list[Alert]:
        """Evaluate all alert rules.

        Returns:
            List of newly fired alerts
        """
        new_alerts: list[Alert] = []
        now = datetime.utcnow()

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Get current metric value
            values = self._metric_values.get(rule.metric_name, [])
            if not values:
                continue

            current_value = values[-1][1]

            # Evaluate condition
            condition_met = rule.evaluate(current_value)

            # Check duration requirement
            if rule.duration_seconds > 0 and condition_met:
                cutoff = now - timedelta(seconds=rule.duration_seconds)
                duration_values = [(ts, v) for ts, v in values if ts >= cutoff]

                if not duration_values or not all(
                    rule.evaluate(v) for _, v in duration_values
                ):
                    condition_met = False

            # Update rule state
            rule.last_evaluation = now

            # Find existing alert for this rule
            existing_alert = None
            for alert in self._alerts.values():
                if alert.rule_id == rule.rule_id and alert.status == AlertStatus.FIRING:
                    existing_alert = alert
                    break

            if condition_met:
                if existing_alert:
                    # Update existing alert
                    existing_alert.current_value = current_value
                    self._maybe_notify(existing_alert)
                else:
                    # Create new alert
                    if not rule.firing_since:
                        rule.firing_since = now

                    alert = self._create_alert(rule, current_value)

                    # Check if silenced
                    if self._is_silenced(alert):
                        alert.status = AlertStatus.SILENCED
                    else:
                        alert.status = AlertStatus.FIRING
                        new_alerts.append(alert)
                        self._notify(alert)

                    self._alerts[alert.alert_id] = alert
            else:
                # Resolve existing alert
                if existing_alert:
                    existing_alert.status = AlertStatus.RESOLVED
                    existing_alert.resolved_at = now
                    self._alert_history.append(existing_alert)

                    if len(self._alert_history) > self._max_history:
                        self._alert_history = self._alert_history[-self._max_history :]

                    del self._alerts[existing_alert.alert_id]

                rule.firing_since = None

        return new_alerts

    def _create_alert(self, rule: AlertRule, current_value: float) -> Alert:
        """Create alert from rule.

        Args:
            rule: Alert rule
            current_value: Current metric value

        Returns:
            New alert
        """
        # Build message
        condition_str = {
            AlertCondition.GREATER_THAN: ">",
            AlertCondition.LESS_THAN: "<",
            AlertCondition.EQUALS: "==",
            AlertCondition.NOT_EQUALS: "!=",
            AlertCondition.GREATER_OR_EQUAL: ">=",
            AlertCondition.LESS_OR_EQUAL: "<=",
        }.get(rule.condition, "?")

        message = (
            f"{rule.name}: {rule.metric_name} is {current_value:.2f} "
            f"({condition_str} {rule.threshold})"
        )

        return Alert(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold=rule.threshold,
            labels=rule.labels.copy(),
            annotations=rule.annotations.copy(),
        )

    def _is_silenced(self, alert: Alert) -> bool:
        """Check if alert is silenced.

        Args:
            alert: Alert to check

        Returns:
            True if silenced
        """
        now = datetime.utcnow()

        for silence in self._silences:
            if silence.starts_at <= now <= silence.ends_at:
                # Check if matchers match alert labels
                matches = all(
                    alert.labels.get(key) == value
                    for key, value in silence.matchers.items()
                )
                if matches:
                    return True

        return False

    def _notify(self, alert: Alert) -> None:
        """Send notification for alert.

        Args:
            alert: Alert to notify
        """
        alert.notification_count += 1
        alert.last_notified_at = datetime.utcnow()

        for notifier in self._notifiers:
            try:
                notifier(alert)
            except Exception:
                pass  # Don't let notifier errors affect alerting

    def _maybe_notify(self, alert: Alert) -> None:
        """Maybe send repeat notification.

        Args:
            alert: Alert to maybe notify
        """
        now = datetime.utcnow()

        if alert.last_notified_at:
            elapsed = (now - alert.last_notified_at).total_seconds()
            if elapsed < self._notification_interval:
                return

        self._notify(alert)

    def add_notifier(self, notifier: Callable[[Alert], None]) -> None:
        """Add notification handler.

        Args:
            notifier: Callable that receives alerts
        """
        self._notifiers.append(notifier)

    def remove_notifier(self, notifier: Callable[[Alert], None]) -> None:
        """Remove notification handler."""
        if notifier in self._notifiers:
            self._notifiers.remove(notifier)

    def add_silence(self, silence: SilenceRule) -> None:
        """Add silence rule.

        Args:
            silence: Silence rule to add
        """
        self._silences.append(silence)

    def remove_silence(self, silence_id: str) -> bool:
        """Remove silence rule.

        Args:
            silence_id: Silence ID to remove

        Returns:
            True if removed
        """
        for i, s in enumerate(self._silences):
            if s.silence_id == silence_id:
                self._silences.pop(i)
                return True
        return False

    def get_firing_alerts(self) -> list[Alert]:
        """Get currently firing alerts.

        Returns:
            List of firing alerts
        """
        return [
            a for a in self._alerts.values() if a.status == AlertStatus.FIRING
        ]

    def get_alert(self, alert_id: str) -> Alert | None:
        """Get alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert or None
        """
        return self._alerts.get(alert_id)

    def get_alert_history(
        self,
        rule_id: str | None = None,
        severity: AlertSeverity | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alert history.

        Args:
            rule_id: Filter by rule ID
            severity: Filter by severity
            limit: Maximum alerts to return

        Returns:
            List of historical alerts
        """
        history = self._alert_history.copy()

        if rule_id:
            history = [a for a in history if a.rule_id == rule_id]

        if severity:
            history = [a for a in history if a.severity == severity]

        return history[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge alert (prevents repeat notifications).

        Args:
            alert_id: Alert ID

        Returns:
            True if acknowledged
        """
        alert = self._alerts.get(alert_id)
        if alert:
            # Reset notification timer to maximum
            alert.last_notified_at = datetime.utcnow()
            return True
        return False

    def clear_all(self) -> None:
        """Clear all alerts and rules."""
        self._rules.clear()
        self._alerts.clear()
        self._silences.clear()
        self._alert_history.clear()
        self._metric_values.clear()


# =============================================================================
# Standard Alert Rules
# =============================================================================


def create_high_error_rate_rule(threshold: float = 5.0) -> AlertRule:
    """Create high error rate alert rule.

    Args:
        threshold: Error rate percentage threshold

    Returns:
        Alert rule
    """
    return AlertRule(
        name="High Error Rate",
        description="Error rate exceeds threshold",
        metric_name="error_rate",
        condition=AlertCondition.GREATER_THAN,
        threshold=threshold,
        duration_seconds=300,
        severity=AlertSeverity.ERROR,
        labels={"category": "reliability"},
    )


def create_high_latency_rule(threshold_ms: float = 1000.0) -> AlertRule:
    """Create high latency alert rule.

    Args:
        threshold_ms: Latency threshold in milliseconds

    Returns:
        Alert rule
    """
    return AlertRule(
        name="High Latency",
        description="P95 latency exceeds threshold",
        metric_name="p95_response_time_ms",
        condition=AlertCondition.GREATER_THAN,
        threshold=threshold_ms,
        duration_seconds=180,
        severity=AlertSeverity.WARNING,
        labels={"category": "performance"},
    )


def create_low_disk_space_rule(threshold_percent: float = 90.0) -> AlertRule:
    """Create low disk space alert rule.

    Args:
        threshold_percent: Disk usage percentage threshold

    Returns:
        Alert rule
    """
    return AlertRule(
        name="Low Disk Space",
        description="Disk usage exceeds threshold",
        metric_name="disk_usage_percent",
        condition=AlertCondition.GREATER_THAN,
        threshold=threshold_percent,
        duration_seconds=0,
        severity=AlertSeverity.CRITICAL,
        labels={"category": "infrastructure"},
    )


def create_high_memory_rule(threshold_percent: float = 85.0) -> AlertRule:
    """Create high memory usage alert rule.

    Args:
        threshold_percent: Memory usage percentage threshold

    Returns:
        Alert rule
    """
    return AlertRule(
        name="High Memory Usage",
        description="Memory usage exceeds threshold",
        metric_name="memory_usage_percent",
        condition=AlertCondition.GREATER_THAN,
        threshold=threshold_percent,
        duration_seconds=300,
        severity=AlertSeverity.WARNING,
        labels={"category": "infrastructure"},
    )


# =============================================================================
# Factory Functions
# =============================================================================


_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """Get singleton alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def create_alert_manager(
    notification_interval_seconds: int = 300,
) -> AlertManager:
    """Create new alert manager."""
    return AlertManager(notification_interval_seconds=notification_interval_seconds)
