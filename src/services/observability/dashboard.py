"""
Dashboard Configuration Service.
Source: Design Document Section 5.3 - Monitoring & Observability
Verified: 2025-12-18

Provides Grafana dashboard configuration generation.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PanelType(str, Enum):
    """Dashboard panel types."""

    GRAPH = "graph"
    STAT = "stat"
    GAUGE = "gauge"
    TABLE = "table"
    HEATMAP = "heatmap"
    BAR_GAUGE = "bargauge"
    TIME_SERIES = "timeseries"
    PIE_CHART = "piechart"
    TEXT = "text"
    ALERT_LIST = "alertlist"
    LOGS = "logs"


class PanelThreshold(BaseModel):
    """Panel threshold for coloring."""

    value: float
    color: str = "green"
    operator: str = "gt"  # gt, lt


class DashboardPanel(BaseModel):
    """Dashboard panel configuration."""

    panel_id: int = Field(default_factory=lambda: int(uuid4().int % 100000))
    title: str
    panel_type: PanelType = PanelType.TIME_SERIES

    # Layout
    x: int = 0
    y: int = 0
    width: int = 12
    height: int = 8

    # Data
    queries: list[dict[str, Any]] = Field(default_factory=list)
    datasource: str = "Prometheus"

    # Display options
    description: Optional[str] = None
    unit: Optional[str] = None
    decimals: Optional[int] = None
    thresholds: list[PanelThreshold] = Field(default_factory=list)

    # Colors
    color_mode: str = "palette-classic"
    fill_opacity: int = 10
    line_width: int = 1

    # Legend
    show_legend: bool = True
    legend_placement: str = "bottom"

    def to_grafana(self) -> dict:
        """Convert to Grafana panel JSON.

        Returns:
            Grafana panel configuration
        """
        panel = {
            "id": self.panel_id,
            "title": self.title,
            "type": self.panel_type.value,
            "gridPos": {
                "x": self.x,
                "y": self.y,
                "w": self.width,
                "h": self.height,
            },
            "datasource": {"type": "prometheus", "uid": self.datasource},
            "targets": self.queries,
            "options": {},
            "fieldConfig": {
                "defaults": {
                    "custom": {
                        "fillOpacity": self.fill_opacity,
                        "lineWidth": self.line_width,
                    },
                },
                "overrides": [],
            },
        }

        # Add description
        if self.description:
            panel["description"] = self.description

        # Add unit
        if self.unit:
            panel["fieldConfig"]["defaults"]["unit"] = self.unit

        # Add decimals
        if self.decimals is not None:
            panel["fieldConfig"]["defaults"]["decimals"] = self.decimals

        # Add thresholds
        if self.thresholds:
            panel["fieldConfig"]["defaults"]["thresholds"] = {
                "mode": "absolute",
                "steps": [
                    {"value": t.value, "color": t.color} for t in self.thresholds
                ],
            }

        # Add legend options
        if self.panel_type in [PanelType.GRAPH, PanelType.TIME_SERIES]:
            panel["options"]["legend"] = {
                "displayMode": "list",
                "placement": self.legend_placement,
                "showLegend": self.show_legend,
            }

        return panel


class DashboardRow(BaseModel):
    """Dashboard row for grouping panels."""

    title: str
    collapsed: bool = False
    panels: list[DashboardPanel] = Field(default_factory=list)
    y_offset: int = 0

    def to_grafana(self) -> dict:
        """Convert to Grafana row JSON.

        Returns:
            Grafana row configuration
        """
        return {
            "title": self.title,
            "type": "row",
            "collapsed": self.collapsed,
            "panels": [p.to_grafana() for p in self.panels],
        }


class Dashboard(BaseModel):
    """Dashboard configuration."""

    uid: str = Field(default_factory=lambda: uuid4().hex[:8])
    title: str
    description: Optional[str] = None

    # Tags
    tags: list[str] = Field(default_factory=list)

    # Time settings
    time_from: str = "now-1h"
    time_to: str = "now"
    refresh: str = "30s"

    # Panels
    panels: list[DashboardPanel] = Field(default_factory=list)
    rows: list[DashboardRow] = Field(default_factory=list)

    # Variables
    variables: list[dict[str, Any]] = Field(default_factory=list)

    # Annotations
    annotations: list[dict[str, Any]] = Field(default_factory=list)

    # Version info
    version: int = 1
    schema_version: int = 39

    def to_grafana(self) -> dict:
        """Convert to Grafana dashboard JSON.

        Returns:
            Grafana dashboard configuration
        """
        # Collect all panels
        all_panels = [p.to_grafana() for p in self.panels]

        # Add row panels
        y_offset = 0
        for row in self.rows:
            row_panel = {
                "id": int(uuid4().int % 100000),
                "title": row.title,
                "type": "row",
                "collapsed": row.collapsed,
                "gridPos": {"x": 0, "y": y_offset, "w": 24, "h": 1},
                "panels": [],
            }
            y_offset += 1

            for panel in row.panels:
                panel_config = panel.to_grafana()
                panel_config["gridPos"]["y"] += y_offset
                if row.collapsed:
                    row_panel["panels"].append(panel_config)
                else:
                    all_panels.append(panel_config)
                y_offset = max(y_offset, panel_config["gridPos"]["y"] + panel_config["gridPos"]["h"])

            all_panels.append(row_panel)

        dashboard = {
            "uid": self.uid,
            "title": self.title,
            "tags": self.tags,
            "style": "dark",
            "timezone": "browser",
            "editable": True,
            "hideControls": False,
            "graphTooltip": 1,
            "panels": all_panels,
            "time": {"from": self.time_from, "to": self.time_to},
            "refresh": self.refresh,
            "schemaVersion": self.schema_version,
            "version": self.version,
            "templating": {"list": self.variables},
            "annotations": {"list": self.annotations},
        }

        if self.description:
            dashboard["description"] = self.description

        return dashboard

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string.

        Args:
            indent: JSON indentation

        Returns:
            JSON string
        """
        return json.dumps(self.to_grafana(), indent=indent)


class DashboardBuilder:
    """Builder for creating dashboards."""

    def __init__(self, title: str):
        """Initialize dashboard builder.

        Args:
            title: Dashboard title
        """
        self._dashboard = Dashboard(title=title)
        self._next_panel_id = 1
        self._current_y = 0

    def with_description(self, description: str) -> "DashboardBuilder":
        """Set dashboard description.

        Args:
            description: Dashboard description

        Returns:
            Self for chaining
        """
        self._dashboard.description = description
        return self

    def with_tags(self, *tags: str) -> "DashboardBuilder":
        """Add dashboard tags.

        Args:
            tags: Tags to add

        Returns:
            Self for chaining
        """
        self._dashboard.tags.extend(tags)
        return self

    def with_time_range(
        self,
        from_time: str = "now-1h",
        to_time: str = "now",
    ) -> "DashboardBuilder":
        """Set time range.

        Args:
            from_time: Start time
            to_time: End time

        Returns:
            Self for chaining
        """
        self._dashboard.time_from = from_time
        self._dashboard.time_to = to_time
        return self

    def with_refresh(self, interval: str) -> "DashboardBuilder":
        """Set refresh interval.

        Args:
            interval: Refresh interval (e.g., "30s", "1m")

        Returns:
            Self for chaining
        """
        self._dashboard.refresh = interval
        return self

    def add_variable(
        self,
        name: str,
        query: str,
        label: str | None = None,
        datasource: str = "Prometheus",
    ) -> "DashboardBuilder":
        """Add template variable.

        Args:
            name: Variable name
            query: Query for values
            label: Display label
            datasource: Data source

        Returns:
            Self for chaining
        """
        variable = {
            "name": name,
            "type": "query",
            "query": query,
            "datasource": {"type": "prometheus", "uid": datasource},
            "label": label or name,
            "hide": 0,
            "multi": False,
            "includeAll": True,
            "refresh": 1,
        }
        self._dashboard.variables.append(variable)
        return self

    def add_panel(
        self,
        title: str,
        query: str,
        panel_type: PanelType = PanelType.TIME_SERIES,
        width: int = 12,
        height: int = 8,
        unit: str | None = None,
        thresholds: list[tuple[float, str]] | None = None,
        legend_label: str | None = None,
    ) -> "DashboardBuilder":
        """Add panel to dashboard.

        Args:
            title: Panel title
            query: PromQL query
            panel_type: Panel type
            width: Panel width
            height: Panel height
            unit: Value unit
            thresholds: List of (value, color) tuples
            legend_label: Legend label

        Returns:
            Self for chaining
        """
        # Build query target
        target = {
            "expr": query,
            "refId": "A",
            "legendFormat": legend_label or "{{instance}}",
        }

        # Build thresholds
        panel_thresholds = []
        if thresholds:
            for value, color in thresholds:
                panel_thresholds.append(PanelThreshold(value=value, color=color))

        # Calculate position
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
            thresholds=panel_thresholds,
        )

        self._dashboard.panels.append(panel)
        self._next_panel_id += 1

        return self

    def add_stat_panel(
        self,
        title: str,
        query: str,
        unit: str | None = None,
        thresholds: list[tuple[float, str]] | None = None,
        width: int = 6,
        height: int = 4,
    ) -> "DashboardBuilder":
        """Add stat panel.

        Args:
            title: Panel title
            query: PromQL query
            unit: Value unit
            thresholds: Thresholds
            width: Panel width
            height: Panel height

        Returns:
            Self for chaining
        """
        return self.add_panel(
            title=title,
            query=query,
            panel_type=PanelType.STAT,
            width=width,
            height=height,
            unit=unit,
            thresholds=thresholds,
        )

    def add_gauge_panel(
        self,
        title: str,
        query: str,
        unit: str | None = None,
        thresholds: list[tuple[float, str]] | None = None,
        width: int = 6,
        height: int = 6,
    ) -> "DashboardBuilder":
        """Add gauge panel.

        Args:
            title: Panel title
            query: PromQL query
            unit: Value unit
            thresholds: Thresholds
            width: Panel width
            height: Panel height

        Returns:
            Self for chaining
        """
        return self.add_panel(
            title=title,
            query=query,
            panel_type=PanelType.GAUGE,
            width=width,
            height=height,
            unit=unit,
            thresholds=thresholds,
        )

    def add_row(self, title: str, collapsed: bool = False) -> "DashboardBuilder":
        """Add row separator.

        Args:
            title: Row title
            collapsed: Whether row is collapsed

        Returns:
            Self for chaining
        """
        row = DashboardRow(title=title, collapsed=collapsed)
        self._dashboard.rows.append(row)
        self._current_y += 1
        return self

    def build(self) -> Dashboard:
        """Build and return dashboard.

        Returns:
            Configured dashboard
        """
        return self._dashboard


# =============================================================================
# Pre-built Dashboards
# =============================================================================


def create_claims_dashboard() -> Dashboard:
    """Create claims processing dashboard.

    Returns:
        Claims dashboard configuration
    """
    builder = DashboardBuilder("Claims Processing Dashboard")

    builder.with_description("Monitor claims processing metrics and performance")
    builder.with_tags("claims", "processing", "healthcare")
    builder.with_time_range("now-6h", "now")
    builder.with_refresh("30s")

    # Overview row
    builder.add_stat_panel(
        "Total Claims",
        'sum(claims_total{job="claims-processor"})',
        unit="short",
        width=4,
    )
    builder.add_stat_panel(
        "Success Rate",
        'sum(rate(claims_success_total[5m])) / sum(rate(claims_total[5m])) * 100',
        unit="percent",
        thresholds=[(95, "green"), (80, "yellow"), (0, "red")],
        width=4,
    )
    builder.add_stat_panel(
        "Error Rate",
        'sum(rate(claims_errors_total[5m])) / sum(rate(claims_total[5m])) * 100',
        unit="percent",
        thresholds=[(5, "green"), (10, "yellow"), (0, "red")],
        width=4,
    )
    builder.add_stat_panel(
        "Avg Processing Time",
        'avg(claims_processing_duration_seconds_sum / claims_processing_duration_seconds_count)',
        unit="s",
        thresholds=[(2, "green"), (5, "yellow")],
        width=4,
    )
    builder.add_stat_panel(
        "Active Claims",
        'claims_in_progress{job="claims-processor"}',
        unit="short",
        width=4,
    )
    builder.add_stat_panel(
        "Queue Depth",
        'claims_queue_depth{job="claims-processor"}',
        unit="short",
        thresholds=[(100, "green"), (500, "yellow")],
        width=4,
    )

    # Throughput graph
    builder.add_panel(
        "Claims Throughput",
        'rate(claims_total{job="claims-processor"}[5m])',
        panel_type=PanelType.TIME_SERIES,
        width=12,
        height=8,
        unit="reqps",
        legend_label="{{status}}",
    )

    # Latency graph
    builder.add_panel(
        "Processing Latency",
        'histogram_quantile(0.95, rate(claims_processing_duration_seconds_bucket[5m]))',
        panel_type=PanelType.TIME_SERIES,
        width=12,
        height=8,
        unit="s",
        legend_label="p95",
    )

    # Status breakdown
    builder.add_panel(
        "Claims by Status",
        'sum by (status) (claims_by_status{job="claims-processor"})',
        panel_type=PanelType.PIE_CHART,
        width=8,
        height=8,
        legend_label="{{status}}",
    )

    # Error breakdown
    builder.add_panel(
        "Errors by Type",
        'sum by (error_type) (rate(claims_errors_total[5m]))',
        panel_type=PanelType.BAR_GAUGE,
        width=8,
        height=8,
        legend_label="{{error_type}}",
    )

    return builder.build()


def create_system_dashboard() -> Dashboard:
    """Create system metrics dashboard.

    Returns:
        System dashboard configuration
    """
    builder = DashboardBuilder("System Metrics Dashboard")

    builder.with_description("Monitor system health and resource usage")
    builder.with_tags("system", "infrastructure")
    builder.with_time_range("now-1h", "now")
    builder.with_refresh("10s")

    # CPU metrics
    builder.add_gauge_panel(
        "CPU Usage",
        '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        unit="percent",
        thresholds=[(70, "green"), (85, "yellow"), (95, "red")],
    )

    # Memory metrics
    builder.add_gauge_panel(
        "Memory Usage",
        '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
        unit="percent",
        thresholds=[(70, "green"), (85, "yellow"), (95, "red")],
    )

    # Disk metrics
    builder.add_gauge_panel(
        "Disk Usage",
        '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
        unit="percent",
        thresholds=[(70, "green"), (85, "yellow"), (95, "red")],
    )

    # Network metrics
    builder.add_panel(
        "Network I/O",
        'rate(node_network_receive_bytes_total[5m])',
        panel_type=PanelType.TIME_SERIES,
        width=12,
        unit="Bps",
        legend_label="{{device}}",
    )

    return builder.build()
