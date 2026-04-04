# mara_host/observability/events.py
"""
Observable event schema for cross-layer observability.

Provides a unified event format for tracking events across MCU, transport,
host, and MCP layers with timestamp correlation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventLayer(str, Enum):
    """Layer where the event originated."""

    MCU = "mcu"
    TRANSPORT = "transport"
    HOST = "host"
    MCP = "mcp"


class EventType(str, Enum):
    """Category of event."""

    MEASUREMENT = "measurement"  # Sensor readings, signal values
    STATE_CHANGE = "state_change"  # Mode transitions, connection state
    ERROR = "error"  # Failures, timeouts, CRC errors
    METRIC = "metric"  # Performance metrics, latency, throughput


@dataclass
class ObservableEvent:
    """
    Unified event schema for cross-layer observability.

    Attributes:
        mcu_ts_ms: MCU uptime in milliseconds (from telemetry). None if not from MCU.
        host_ts_ms: Host wall clock in milliseconds (always present).
        layer: Which layer generated the event (MCU, transport, host, MCP).
        source: Subsystem within the layer (e.g., "imu", "commander", "serial").
        event_type: Category of event (measurement, state_change, error, metric).
        value: Single numeric value (for simple measurements).
        values: Multiple named values (for compound metrics).
        state: State name (for state_change events).
        error: Error message (for error events).
        metadata: Additional context (axis, slot_id, etc.).

    Examples:
        # IMU measurement from MCU
        ObservableEvent(
            mcu_ts_ms=12345,
            host_ts_ms=1712345678000,
            layer=EventLayer.MCU,
            source="imu",
            event_type=EventType.MEASUREMENT,
            value=9.81,
            metadata={"axis": "az"},
        )

        # Transport error
        ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.TRANSPORT,
            source="serial",
            event_type=EventType.ERROR,
            error="CRC mismatch",
            metadata={"bytes_skipped": 5},
        )

        # Commander latency metrics
        ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.HOST,
            source="commander",
            event_type=EventType.METRIC,
            values={"avg_latency_ms": 12.5, "p99_latency_ms": 45.0},
        )
    """

    # Timestamps
    mcu_ts_ms: int | None  # MCU uptime (from telemetry)
    host_ts_ms: int  # Host wall clock

    # Event identification
    layer: EventLayer | str  # "mcu" | "transport" | "host" | "mcp"
    source: str  # Subsystem: "imu", "commander", etc.
    event_type: EventType | str  # "measurement" | "state_change" | "error" | "metric"

    # Event data (use appropriate field for event type)
    value: float | None = None
    values: dict[str, float] | None = None
    state: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d: dict[str, Any] = {
            "host_ts_ms": self.host_ts_ms,
            "layer": self.layer.value if isinstance(self.layer, EventLayer) else self.layer,
            "source": self.source,
            "event_type": (
                self.event_type.value
                if isinstance(self.event_type, EventType)
                else self.event_type
            ),
        }
        if self.mcu_ts_ms is not None:
            d["mcu_ts_ms"] = self.mcu_ts_ms
        if self.value is not None:
            d["value"] = self.value
        if self.values is not None:
            d["values"] = self.values
        if self.state is not None:
            d["state"] = self.state
        if self.error is not None:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ObservableEvent:
        """Create from dictionary."""
        return cls(
            mcu_ts_ms=d.get("mcu_ts_ms"),
            host_ts_ms=d["host_ts_ms"],
            layer=d["layer"],
            source=d["source"],
            event_type=d["event_type"],
            value=d.get("value"),
            values=d.get("values"),
            state=d.get("state"),
            error=d.get("error"),
            metadata=d.get("metadata"),
        )
