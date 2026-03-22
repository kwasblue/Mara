# tests/test_mcp_runtime.py
"""Tests for MCP runtime."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from mara_host.mcp.runtime import MaraRuntime, StateStore, FreshValue, EventType


class TestStateStore:
    """Tests for StateStore."""

    def test_initial_state(self):
        """Test initial state values."""
        store = StateStore()
        assert store.connected is False
        assert store.connected_at is None
        assert store.robot_state.value == "UNKNOWN"
        assert store.command_seq == 0

    def test_next_seq(self):
        """Test command sequence generation."""
        store = StateStore()
        assert store.next_seq() == 1
        assert store.next_seq() == 2
        assert store.next_seq() == 3

    def test_add_event(self):
        """Test event tracking."""
        store = StateStore()
        event = store.add_event(EventType.CONNECTED, {"test": "data"})

        assert event.type == EventType.CONNECTED
        assert event.data == {"test": "data"}
        assert len(store.events) == 1

    def test_event_trimming(self):
        """Test event list is trimmed."""
        store = StateStore()
        store.max_events = 5

        for i in range(10):
            store.add_event(EventType.TELEMETRY, {"i": i})

        assert len(store.events) == 5
        # Should have the last 5 events
        assert store.events[0].data["i"] == 5

    def test_get_recent_events_filtered(self):
        """Test filtering events by type."""
        store = StateStore()
        store.add_event(EventType.CONNECTED)
        store.add_event(EventType.TELEMETRY, {"x": 1})
        store.add_event(EventType.TELEMETRY, {"x": 2})
        store.add_event(EventType.DISCONNECTED)

        telemetry_events = store.get_recent_events(10, EventType.TELEMETRY)
        assert len(telemetry_events) == 2

    def test_command_stats_empty(self):
        """Test command stats with no commands."""
        store = StateStore()
        stats = store.get_command_stats()

        assert stats["total"] == 0
        assert stats["success_rate"] == 0


class TestFreshValue:
    """Tests for FreshValue."""

    def test_freshness_states(self):
        """Test freshness transitions."""
        # Fresh when just created
        fv = FreshValue("test", datetime.now(), stale_after_s=1.0)
        assert fv.freshness == "fresh"
        assert not fv.is_stale

    def test_to_dict(self):
        """Test serialization."""
        fv = FreshValue("test_value", datetime.now(), stale_after_s=5.0)
        d = fv.to_dict()

        assert d["value"] == "test_value"
        assert "age_s" in d
        assert d["freshness"] in ["fresh", "aging", "stale"]


class TestMaraRuntime:
    """Tests for MaraRuntime."""

    @pytest.fixture
    def runtime(self):
        """Create a fresh runtime instance."""
        return MaraRuntime()

    def test_initial_state(self, runtime):
        """Test initial runtime state."""
        assert not runtime.is_connected
        assert runtime.state.connected is False

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock CLIContext."""
        ctx = MagicMock()
        ctx.is_connected = True
        ctx.client = MagicMock()
        ctx.client.firmware_version = "1.0.0"
        ctx.client.protocol_version = 2
        ctx.client.features = ["motor", "servo"]

        # Mock services
        ctx.state_service = MagicMock()
        ctx.state_service.arm = AsyncMock(return_value=MagicMock(ok=True, state="ARMED"))
        ctx.state_service.disarm = AsyncMock(return_value=MagicMock(ok=True, state="IDLE"))

        ctx.servo_service = MagicMock()
        ctx.motor_service = MagicMock()
        ctx.gpio_service = MagicMock()

        # Mock telemetry
        ctx._telemetry = MagicMock()
        ctx._telemetry.on_imu = MagicMock()
        ctx._telemetry.on_encoder = MagicMock()
        ctx._telemetry.on_state = MagicMock()

        return ctx

    @pytest.mark.asyncio
    async def test_ensure_armed_uses_state_service(self, runtime, mock_ctx):
        """Test that ensure_armed uses state_service, not direct client."""
        runtime._ctx = mock_ctx
        runtime._store.connected = True

        await runtime.ensure_armed()

        # Should use state_service.arm(), not client.arm()
        mock_ctx.state_service.arm.assert_called_once()
        mock_ctx.client.arm.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_armed_updates_store(self, runtime, mock_ctx):
        """Test that ensure_armed updates state store."""
        runtime._ctx = mock_ctx
        runtime._store.connected = True

        await runtime.ensure_armed()

        assert runtime._store.robot_state.value == "ARMED"

    def test_state_service_property(self, runtime, mock_ctx):
        """Test state_service property access."""
        runtime._ctx = mock_ctx

        svc = runtime.state_service
        assert svc == mock_ctx.state_service

    def test_state_service_property_not_connected(self, runtime):
        """Test state_service raises when not connected."""
        with pytest.raises(RuntimeError, match="Not connected"):
            _ = runtime.state_service

    def test_servo_service_property(self, runtime, mock_ctx):
        """Test servo_service property access."""
        runtime._ctx = mock_ctx
        assert runtime.servo_service == mock_ctx.servo_service

    def test_motor_service_property(self, runtime, mock_ctx):
        """Test motor_service property access."""
        runtime._ctx = mock_ctx
        assert runtime.motor_service == mock_ctx.motor_service

    def test_record_command(self, runtime):
        """Test command recording."""
        sent_at = datetime.now()
        record = runtime.record_command(
            command="test_cmd",
            params={"a": 1},
            success=True,
            error=None,
            sent_at=sent_at,
        )

        assert record.command == "test_cmd"
        assert record.success is True
        assert record.latency_ms is not None
        assert len(runtime.state.commands) == 1

    def test_get_snapshot(self, runtime):
        """Test state snapshot generation."""
        snapshot = runtime.get_snapshot()

        assert "connected" in snapshot
        assert "robot_state" in snapshot
        assert "command_stats" in snapshot
        assert "recent_commands" in snapshot

    def test_get_freshness_report(self, runtime):
        """Test freshness report generation."""
        report = runtime.get_freshness_report()

        assert "robot_state" in report
        assert "imu" in report
        assert "any_stale" in report
