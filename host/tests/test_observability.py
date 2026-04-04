# tests/test_observability.py
"""
Tests for the observability infrastructure.

Priority: MEDIUM - ObservabilityBus is foundation for cross-layer diagnostics.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from mara_host.observability.events import (
    EventLayer,
    EventType,
    ObservableEvent,
)
from mara_host.observability.recording import (
    ObservabilityBus,
    RecordingEventBus,  # Legacy alias
)


# ═══════════════════════════════════════════════════════════════════════════
# ObservableEvent Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestObservableEvent:
    """Tests for ObservableEvent schema."""

    def test_measurement_event(self):
        """Test creating a measurement event."""
        event = ObservableEvent(
            mcu_ts_ms=12345,
            host_ts_ms=1712345678000,
            layer=EventLayer.MCU,
            source="imu",
            event_type=EventType.MEASUREMENT,
            value=9.81,
            metadata={"axis": "az"},
        )

        assert event.mcu_ts_ms == 12345
        assert event.layer == EventLayer.MCU
        assert event.source == "imu"
        assert event.value == 9.81
        assert event.metadata["axis"] == "az"

    def test_error_event(self):
        """Test creating an error event."""
        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.TRANSPORT,
            source="serial",
            event_type=EventType.ERROR,
            error="CRC mismatch",
        )

        assert event.mcu_ts_ms is None
        assert event.layer == EventLayer.TRANSPORT
        assert event.error == "CRC mismatch"

    def test_metric_event(self):
        """Test creating a metric event."""
        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.HOST,
            source="commander",
            event_type=EventType.METRIC,
            values={"avg_latency_ms": 12.5, "p99_latency_ms": 45.0},
        )

        assert event.values["avg_latency_ms"] == 12.5
        assert event.values["p99_latency_ms"] == 45.0

    def test_state_change_event(self):
        """Test creating a state change event."""
        event = ObservableEvent(
            mcu_ts_ms=1000,
            host_ts_ms=1712345678000,
            layer=EventLayer.MCU,
            source="mode",
            event_type=EventType.STATE_CHANGE,
            state="ARMED",
        )

        assert event.state == "ARMED"

    def test_to_dict_serialization(self):
        """Test event serialization to dict."""
        event = ObservableEvent(
            mcu_ts_ms=12345,
            host_ts_ms=1712345678000,
            layer=EventLayer.MCU,
            source="imu",
            event_type=EventType.MEASUREMENT,
            value=9.81,
            metadata={"axis": "az"},
        )

        d = event.to_dict()

        assert d["mcu_ts_ms"] == 12345
        assert d["host_ts_ms"] == 1712345678000
        assert d["layer"] == "mcu"
        assert d["source"] == "imu"
        assert d["event_type"] == "measurement"
        assert d["value"] == 9.81
        assert d["metadata"]["axis"] == "az"

    def test_to_dict_omits_none_values(self):
        """Test that None values are omitted from serialization."""
        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={"count": 5},
        )

        d = event.to_dict()

        assert "mcu_ts_ms" not in d
        assert "value" not in d
        assert "error" not in d
        assert "state" not in d

    def test_from_dict_deserialization(self):
        """Test event deserialization from dict."""
        d = {
            "mcu_ts_ms": 12345,
            "host_ts_ms": 1712345678000,
            "layer": "mcu",
            "source": "imu",
            "event_type": "measurement",
            "value": 9.81,
            "metadata": {"axis": "az"},
        }

        event = ObservableEvent.from_dict(d)

        assert event.mcu_ts_ms == 12345
        assert event.layer == "mcu"
        assert event.value == 9.81

    def test_string_layer_accepted(self):
        """Test that string layer values are accepted."""
        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer="custom",  # Not an enum value
            source="test",
            event_type="custom_event",
        )

        assert event.layer == "custom"
        d = event.to_dict()
        assert d["layer"] == "custom"


# ═══════════════════════════════════════════════════════════════════════════
# ObservabilityBus Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestObservabilityBus:
    """Tests for ObservabilityBus."""

    def test_emit_calls_handlers(self):
        """Test that emit notifies all subscribed handlers."""
        bus = ObservabilityBus()

        received = []

        def handler(event: ObservableEvent):
            received.append(event)

        bus.on_event(handler)

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=int(time.time() * 1000),
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={"count": 1},
        )
        bus.emit(event)

        assert len(received) == 1
        assert received[0] is event

    def test_multiple_handlers(self):
        """Test that multiple handlers all receive events."""
        bus = ObservabilityBus()

        counts = {"a": 0, "b": 0}

        bus.on_event(lambda e: counts.__setitem__("a", counts["a"] + 1))
        bus.on_event(lambda e: counts.__setitem__("b", counts["b"] + 1))

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=int(time.time() * 1000),
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={},
        )
        bus.emit(event)

        assert counts["a"] == 1
        assert counts["b"] == 1

    def test_off_event_unsubscribes(self):
        """Test that off_event removes handler."""
        bus = ObservabilityBus()

        received = []

        def handler(event):
            received.append(event)

        bus.on_event(handler)
        bus.off_event(handler)

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=int(time.time() * 1000),
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={},
        )
        bus.emit(event)

        assert len(received) == 0

    def test_handler_exception_does_not_crash(self):
        """Test that handler exceptions are caught."""
        bus = ObservabilityBus()

        def bad_handler(event):
            raise ValueError("Handler crashed!")

        good_received = []

        def good_handler(event):
            good_received.append(event)

        bus.on_event(bad_handler)
        bus.on_event(good_handler)

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=int(time.time() * 1000),
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={},
        )

        # Should not raise
        bus.emit(event)

        # Good handler should still be called
        assert len(good_received) == 1


# ═══════════════════════════════════════════════════════════════════════════
# MCU Timestamp Sync Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMcuTimestampSync:
    """Tests for MCU/host timestamp correlation."""

    def test_set_mcu_sync_computes_offset(self):
        """Test that set_mcu_sync computes correct offset."""
        bus = ObservabilityBus()

        # Simulate: MCU has been running for 5000ms, host is at some wall time
        with patch("time.time", return_value=1712345678.0):
            bus.set_mcu_sync(5000)

        # Offset should be host_time_ms - mcu_uptime
        expected_offset = 1712345678000 - 5000
        assert bus._mcu_epoch_offset_ms == expected_offset

    def test_mcu_to_host_ts_conversion(self):
        """Test converting MCU timestamp to host time."""
        bus = ObservabilityBus()

        # Set sync point: MCU at 5000ms when host is at 1712345678000ms
        with patch("time.time", return_value=1712345678.0):
            bus.set_mcu_sync(5000)

        # MCU time 10000ms should map to host time 1712345683000ms
        # (5000ms later on MCU = 5000ms later on host)
        host_ts = bus.mcu_to_host_ts(10000)
        expected = 1712345678000 - 5000 + 10000  # 1712345683000
        assert host_ts == expected

    def test_mcu_to_host_ts_without_sync(self):
        """Test conversion without sync (offset = 0)."""
        bus = ObservabilityBus()

        # No sync called, offset defaults to 0
        host_ts = bus.mcu_to_host_ts(12345)
        assert host_ts == 12345  # No offset applied

    def test_sync_updates_offset(self):
        """Test that calling set_mcu_sync again updates offset."""
        bus = ObservabilityBus()

        with patch("time.time", return_value=1000.0):
            bus.set_mcu_sync(100)

        first_offset = bus._mcu_epoch_offset_ms

        with patch("time.time", return_value=2000.0):
            bus.set_mcu_sync(200)

        # Offset should be different now
        assert bus._mcu_epoch_offset_ms != first_offset


# ═══════════════════════════════════════════════════════════════════════════
# Convenience Method Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    """Tests for emit_* convenience methods."""

    def test_emit_measurement(self):
        """Test emit_measurement convenience method."""
        bus = ObservabilityBus()

        received = []
        bus.on_event(received.append)

        bus.emit_measurement(
            EventLayer.MCU,
            "imu",
            value=9.81,
            mcu_ts_ms=1234,
            axis="az",
        )

        assert len(received) == 1
        event = received[0]
        assert event.layer == EventLayer.MCU
        assert event.source == "imu"
        assert event.event_type == EventType.MEASUREMENT
        assert event.value == 9.81
        assert event.mcu_ts_ms == 1234
        assert event.metadata["axis"] == "az"

    def test_emit_metric(self):
        """Test emit_metric convenience method."""
        bus = ObservabilityBus()

        received = []
        bus.on_event(received.append)

        bus.emit_metric(
            EventLayer.HOST,
            "commander",
            {"avg_latency_ms": 12.5, "count": 100},
        )

        assert len(received) == 1
        event = received[0]
        assert event.event_type == EventType.METRIC
        assert event.values["avg_latency_ms"] == 12.5
        assert event.values["count"] == 100

    def test_emit_state_change(self):
        """Test emit_state_change convenience method."""
        bus = ObservabilityBus()

        received = []
        bus.on_event(received.append)

        bus.emit_state_change(
            EventLayer.MCU,
            "mode",
            "ARMED",
            mcu_ts_ms=5000,
        )

        assert len(received) == 1
        event = received[0]
        assert event.event_type == EventType.STATE_CHANGE
        assert event.state == "ARMED"
        assert event.mcu_ts_ms == 5000

    def test_emit_error(self):
        """Test emit_error convenience method."""
        bus = ObservabilityBus()

        received = []
        bus.on_event(received.append)

        bus.emit_error(
            EventLayer.TRANSPORT,
            "serial",
            "CRC mismatch",
            bytes_skipped=5,
        )

        assert len(received) == 1
        event = received[0]
        assert event.event_type == EventType.ERROR
        assert event.error == "CRC mismatch"
        assert event.metadata["bytes_skipped"] == 5


# ═══════════════════════════════════════════════════════════════════════════
# Bundle Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestBundleIntegration:
    """Tests for MaraLogBundle integration."""

    def test_emit_persists_to_bundle(self):
        """Test that emit writes to bundle if configured."""
        # Mock bundle with events writer
        mock_events = MagicMock()
        mock_bundle = MagicMock()
        mock_bundle.events = mock_events

        bus = ObservabilityBus(log_bundle=mock_bundle)

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={"count": 1},
        )
        bus.emit(event)

        # Should have called bundle.events.write
        mock_events.write.assert_called_once()
        call_args = mock_events.write.call_args
        assert call_args[0][0] == "observable"

    def test_emit_works_without_bundle(self):
        """Test that emit works without bundle (standalone mode)."""
        bus = ObservabilityBus()  # No bundle

        received = []
        bus.on_event(received.append)

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={},
        )

        # Should not raise
        bus.emit(event)
        assert len(received) == 1

    def test_bundle_alias_backwards_compat(self):
        """Test that 'bundle' parameter works (backwards compat)."""
        mock_events = MagicMock()
        mock_bundle = MagicMock()
        mock_bundle.events = mock_events

        # Use deprecated 'bundle' parameter
        bus = ObservabilityBus(bundle=mock_bundle)

        event = ObservableEvent(
            mcu_ts_ms=None,
            host_ts_ms=1712345678000,
            layer=EventLayer.HOST,
            source="test",
            event_type=EventType.METRIC,
            values={},
        )
        bus.emit(event)

        # Should still work
        mock_events.write.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# Backwards Compatibility Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestBackwardsCompatibility:
    """Tests for RecordingEventBus backwards compatibility."""

    def test_recording_event_bus_alias_exists(self):
        """Test that RecordingEventBus alias exists."""
        assert RecordingEventBus is ObservabilityBus

    def test_subscribe_alias_works(self):
        """Test that subscribe method works (backwards compat)."""
        mock_inner_bus = MagicMock()
        bus = ObservabilityBus(inner_bus=mock_inner_bus)

        def handler(data):
            pass

        bus.subscribe("test_topic", handler)
        mock_inner_bus.subscribe.assert_called_once_with("test_topic", handler)

    def test_publish_alias_works(self):
        """Test that publish method works (backwards compat)."""
        mock_inner_bus = MagicMock()
        bus = ObservabilityBus(inner_bus=mock_inner_bus)

        bus.publish("test_topic", {"key": "value"})
        mock_inner_bus.publish.assert_called_once_with("test_topic", {"key": "value"})
