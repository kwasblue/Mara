# mara_host/observability/__init__.py
"""
Unified observability layer for MARA.

Provides cross-layer event tracking, timestamp correlation, and metrics collection.

Example usage:
    from mara_host.observability import ObservabilityBus, ObservableEvent, EventLayer

    # Create observability bus (optionally with log bundle for persistence)
    obs = ObservabilityBus(log_bundle=bundle)

    # Sync MCU clock at handshake
    obs.set_mcu_sync(mcu_uptime_ms)

    # Emit events
    obs.emit(ObservableEvent(
        mcu_ts_ms=mcu_ts,
        host_ts_ms=int(time.time() * 1000),
        layer=EventLayer.MCU,
        source="imu",
        event_type=EventType.MEASUREMENT,
        value=9.81,
        metadata={"axis": "az"},
    ))

    # Or use convenience methods
    obs.emit_metric(EventLayer.HOST, "commander", {"avg_latency_ms": 12.5})
    obs.emit_error(EventLayer.TRANSPORT, "serial", "CRC mismatch", bytes_skipped=5)
"""

from .events import (
    ObservableEvent,
    EventLayer,
    EventType,
)
from .recording import (
    ObservabilityBus,
    RecordingTransport,
)

__all__ = [
    "ObservableEvent",
    "EventLayer",
    "EventType",
    "ObservabilityBus",
    "RecordingTransport",
]
