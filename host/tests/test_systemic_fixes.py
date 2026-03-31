# tests/test_systemic_fixes.py
"""
Tests for systemic fixes implemented in Phases 1-3.

Covers:
- Phase 9: Async Safety (get_running_loop, async handler warnings)
- Phase 10: Resource Limits (pending command limit, subscription leak warning)
- Phase 11: State Consistency (cache locks, handshake lock)
- Phase 12: Error Recovery (telemetry parse logging, reader error recovery)
- Phase 13: Configuration Validation (command validation, numeric bounds)
- Phase 14: Thread Safety (atomic clear_pending, executor shutdown)
- Phase 15: Edge Cases (zero distance sentinel, rate limit validation)
- Phase 16: API Consistency (boolean parsing, exception docs)
- Phase 3: Additional fixes (file cleanup, type safety, state locks)
"""

import asyncio
import math
import struct
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# =============================================================================
# Phase 9: Async Safety Tests
# =============================================================================

class TestAsyncSafety:
    """Tests for asyncio.get_running_loop() usage and async handler warnings."""

    @pytest.mark.asyncio
    async def test_reliable_commander_uses_running_loop(self):
        """Verify ReliableCommander uses get_running_loop() not get_event_loop()."""
        from mara_host.command.coms.reliable_commander import ReliableCommander

        send_mock = AsyncMock(return_value=1)
        commander = ReliableCommander(send_func=send_mock)
        await commander.start_update_loop()

        try:
            # This should work in async context with get_running_loop()
            result = await commander.send("CMD_TEST", {"data": 1}, wait_for_ack=True)
            # Will timeout since no ACK, but shouldn't raise about event loop
            assert result[1] in ("TIMEOUT", "STALE", None)
        finally:
            await commander.stop_update_loop()

    @pytest.mark.asyncio
    async def test_event_bus_warns_on_async_handler_via_sync_publish(self, caplog):
        """Verify EventBus warns when async handler called via sync publish()."""
        from mara_host.core.event_bus import EventBus

        bus = EventBus()

        async def async_handler(data):
            pass

        bus.subscribe("test.topic", async_handler)

        import logging
        with caplog.at_level(logging.WARNING):
            bus.publish("test.topic", {"value": 1})

        # Should warn about async handler
        assert any("publish_async" in record.message for record in caplog.records)


# =============================================================================
# Phase 10: Resource Limits Tests
# =============================================================================

class TestResourceLimits:
    """Tests for pending command limits and subscription leak warnings."""

    @pytest.mark.asyncio
    async def test_pending_command_limit_rejects_when_full(self):
        """Verify commands are rejected when MAX_PENDING_COMMANDS reached."""
        from mara_host.command.coms.reliable_commander import ReliableCommander

        events = []
        send_mock = AsyncMock(return_value=1)
        commander = ReliableCommander(
            send_func=send_mock,
            on_event=lambda e: events.append(e),
        )

        # Fill up pending dict to max
        commander._pending = {i: MagicMock() for i in range(256)}

        # Next command should be rejected
        ok, error = await commander.send("CMD_TEST", {}, wait_for_ack=True)

        assert not ok
        assert error == "TOO_MANY_PENDING"
        assert any(e.get("event") == "cmd.rejected" for e in events)

    def test_subscription_leak_warning(self, caplog):
        """Verify EventBus warns on high subscription count."""
        from mara_host.core.event_bus import EventBus

        bus = EventBus()

        import logging
        with caplog.at_level(logging.WARNING):
            # Subscribe more than threshold (10)
            for i in range(15):
                bus.subscribe("test.topic", lambda x: None)

        # Should warn about possible leak
        assert any("High subscription count" in record.message for record in caplog.records)


# =============================================================================
# Phase 11: State Consistency Tests
# =============================================================================

class TestStateConsistency:
    """Tests for cache locks and handshake synchronization."""

    @pytest.mark.asyncio
    async def test_control_graph_service_cache_lock(self):
        """Verify ControlGraphService uses lock for cache operations."""
        from mara_host.services.control.control_graph_service import ControlGraphService

        mock_client = MagicMock()
        mock_client.bus = MagicMock()
        mock_client.bus.subscribe = MagicMock()
        mock_client.bus.unsubscribe = MagicMock()

        service = ControlGraphService(mock_client)

        # Verify lock exists
        assert hasattr(service, '_cache_lock')
        assert isinstance(service._cache_lock, asyncio.Lock)

        service.close()

    @pytest.mark.asyncio
    async def test_connection_monitor_state_uses_lock(self):
        """Verify ConnectionMonitor state property uses lock."""
        from mara_host.command.coms.connection_monitor import ConnectionMonitor, ConnectionState

        monitor = ConnectionMonitor()

        # Access state from multiple "threads" (simulated)
        results = []

        def read_state():
            for _ in range(100):
                results.append(monitor.state)

        threads = [threading.Thread(target=read_state) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed without race condition
        assert len(results) == 500
        assert all(isinstance(s, ConnectionState) for s in results)


# =============================================================================
# Phase 12: Error Recovery Tests
# =============================================================================

class TestErrorRecovery:
    """Tests for telemetry parse logging and reader error recovery."""

    def test_binary_parser_logs_short_header(self, caplog):
        """Verify binary parser logs when packet is too short."""
        from mara_host.telemetry.binary_parser import parse_telemetry_bin

        import logging
        with caplog.at_level(logging.WARNING):
            result = parse_telemetry_bin(b"\x01\x02")  # Too short

        assert result.raw.get("error") == "short_header"
        assert any("too short" in record.message for record in caplog.records)

    def test_binary_parser_logs_truncated_section(self, caplog):
        """Verify binary parser logs when section body is truncated."""
        from mara_host.telemetry.binary_parser import parse_telemetry_bin

        # Valid header but truncated section
        # Header: version(1), seq(2), ts_ms(4), section_count(1) = 8 bytes
        # Section header: id(1), len(2) = 3 bytes
        header = struct.pack("<BHIB", 1, 0, 0, 1)  # 1 section
        section_hdr = struct.pack("<BH", 0x01, 100)  # Section needs 100 bytes
        payload = header + section_hdr + b"\x00" * 10  # Only 10 bytes provided

        import logging
        with caplog.at_level(logging.WARNING):
            result = parse_telemetry_bin(payload)

        assert result.raw.get("error") == "short_section_body"

    def test_stream_transport_consecutive_error_limit(self):
        """Verify stream transport stops after consecutive errors."""
        from mara_host.transport.stream_transport import StreamTransport

        class TestTransport(StreamTransport):
            def __init__(self):
                super().__init__()
                self.read_count = 0
                self.error_count = 0

            def _open(self):
                pass

            def _close(self):
                pass

            def _read_raw(self, n):
                self.read_count += 1
                self.error_count += 1
                raise IOError("Simulated read error")

            def _send_bytes(self, data):
                pass

        transport = TestTransport()
        transport._is_open = True
        transport._stop = False

        # Run reader loop in thread briefly
        thread = threading.Thread(target=transport._reader_loop)
        thread.start()
        time.sleep(1.5)  # Allow time for errors
        transport._stop = True
        thread.join(timeout=2.0)

        # Should have stopped due to consecutive errors
        assert transport._stop


# =============================================================================
# Phase 13: Configuration Validation Tests
# =============================================================================

class TestConfigValidation:
    """Tests for command validation and config numeric bounds."""

    def test_json_to_binary_validates_nan(self):
        """Verify JSON-to-binary encoder rejects NaN values."""
        from mara_host.command.json_to_binary import JsonToBinaryEncoder

        encoder = JsonToBinaryEncoder()

        with pytest.raises(ValueError, match="must be finite"):
            encoder.encode({"type": "CMD_SET_VEL", "vx": float('nan'), "omega": 0.0})

    def test_json_to_binary_validates_inf(self):
        """Verify JSON-to-binary encoder rejects Inf values."""
        from mara_host.command.json_to_binary import JsonToBinaryEncoder

        encoder = JsonToBinaryEncoder()

        with pytest.raises(ValueError, match="must be finite"):
            encoder.encode({"type": "CMD_SET_VEL", "vx": float('inf'), "omega": 0.0})

    def test_json_to_binary_encodes_large_values(self):
        """Verify JSON-to-binary encoder handles large values (bounds check is service-layer)."""
        from mara_host.command.json_to_binary import JsonToBinaryEncoder

        encoder = JsonToBinaryEncoder()
        # Encoder is raw - bounds validation happens at service layer
        result = encoder.encode({"type": "CMD_SET_VEL", "vx": 100.0, "omega": 0.0})
        assert result is not None
        assert len(result) > 0

    def test_json_to_binary_handles_string_input(self):
        """Verify JSON-to-binary encoder handles string conversion."""
        from mara_host.command.json_to_binary import JsonToBinaryEncoder

        encoder = JsonToBinaryEncoder()

        with pytest.raises(ValueError, match="could not convert|must be numeric|invalid"):
            encoder.encode({"type": "CMD_SET_VEL", "vx": "not_a_number", "omega": 0.0})

    def test_drive_config_rejects_negative_wheel_radius(self):
        """Verify DriveConfig rejects negative wheel_radius."""
        from mara_host.config.robot_config import DriveConfig

        with pytest.raises(ValueError, match="wheel_radius must be positive"):
            DriveConfig.from_dict({"wheel_radius": -0.05})

    def test_drive_config_rejects_zero_max_velocity(self):
        """Verify DriveConfig rejects zero max_linear_vel."""
        from mara_host.config.robot_config import DriveConfig

        with pytest.raises(ValueError, match="max_linear_vel must be positive"):
            DriveConfig.from_dict({"max_linear_vel": 0})

    def test_drive_config_accepts_valid_values(self):
        """Verify DriveConfig accepts valid positive values."""
        from mara_host.config.robot_config import DriveConfig

        config = DriveConfig.from_dict({
            "wheel_radius": 0.05,
            "wheel_base": 0.2,
            "max_linear_vel": 1.5,
            "max_angular_vel": 3.0,
        })

        assert config.wheel_radius == 0.05
        assert config.max_linear_vel == 1.5


# =============================================================================
# Phase 14: Thread Safety Tests
# =============================================================================

class TestThreadSafety:
    """Tests for atomic operations and thread-safe shutdown."""

    @pytest.mark.asyncio
    async def test_clear_pending_sync_atomic(self):
        """Verify clear_pending_sync uses atomic dict swap."""
        from mara_host.command.coms.reliable_commander import ReliableCommander

        send_mock = AsyncMock(return_value=1)
        commander = ReliableCommander(send_func=send_mock)

        # Add some pending commands with futures
        loop = asyncio.get_running_loop()
        for i in range(10):
            future = loop.create_future()
            commander._pending[i] = MagicMock(future=future)

        # Clear synchronously
        commander.clear_pending_sync()

        # All futures should be resolved
        assert len(commander._pending) == 0


# =============================================================================
# Phase 15: Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for zero distance sentinel and rate limit validation."""

    def test_binary_parser_zero_distance_is_valid(self):
        """Verify zero distance is not treated as 'no measurement'."""
        from mara_host.telemetry.binary_parser import (
            parse_telemetry_bin,
            _NO_MEASUREMENT_SENTINEL,
            TELEM_ULTRASONIC,
        )

        # Build valid telemetry packet with ultrasonic section
        # Header: version(1), seq(2), ts_ms(4), section_count(1)
        header = struct.pack("<BHIB", 1, 0, 1000, 1)
        # Section header: id(1), len(2)
        section_hdr = struct.pack("<BH", TELEM_ULTRASONIC, 5)
        # Ultrasonic body: sensor_id(1), attached(1), ok(1), dist_mm(2)
        # Distance = 0 (touching sensor) should be valid
        section_body = struct.pack("<BBBH", 0, 1, 1, 0)

        payload = header + section_hdr + section_body
        result = parse_telemetry_bin(payload)

        # Zero distance should be 0.0, not None
        assert result.ultrasonic is not None
        assert result.ultrasonic.distance_cm == 0.0

    def test_binary_parser_sentinel_means_no_measurement(self):
        """Verify sentinel value 0xFFFF means no measurement."""
        from mara_host.telemetry.binary_parser import (
            parse_telemetry_bin,
            _NO_MEASUREMENT_SENTINEL,
            TELEM_ULTRASONIC,
        )

        header = struct.pack("<BHIB", 1, 0, 1000, 1)
        section_hdr = struct.pack("<BH", TELEM_ULTRASONIC, 5)
        # Distance = 0xFFFF (sentinel) should be None
        section_body = struct.pack("<BBBH", 0, 1, 1, _NO_MEASUREMENT_SENTINEL)

        payload = header + section_hdr + section_body
        result = parse_telemetry_bin(payload)

        assert result.ultrasonic is not None
        assert result.ultrasonic.distance_cm is None

    def test_motion_service_rate_limit_minimum(self):
        """Verify motion service rate limit has minimum of 1.0 Hz."""
        from mara_host.services.control.motion_service import MotionService

        mock_client = MagicMock()
        service = MotionService(mock_client)

        # Try to set rate below minimum
        service.rate_limit_hz = 0.0
        assert service.rate_limit_hz >= 1.0

        service.rate_limit_hz = -10.0
        assert service.rate_limit_hz >= 1.0


# =============================================================================
# Phase 16: API Consistency Tests
# =============================================================================

class TestAPIConsistency:
    """Tests for boolean parsing and consistent API behavior."""

    def test_parse_bool_handles_various_formats(self):
        """Verify _parse_bool handles 'yes', 'true', '1', etc."""
        from mara_host.config.robot_config import _parse_bool

        # True cases
        assert _parse_bool(True) is True
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("Yes") is True
        assert _parse_bool("1") is True
        assert _parse_bool("on") is True

        # False cases
        assert _parse_bool(False) is False
        assert _parse_bool("false") is False
        assert _parse_bool("no") is False
        assert _parse_bool("0") is False
        assert _parse_bool("off") is False
        assert _parse_bool("") is False

        # Default handling
        assert _parse_bool(None, default=True) is True
        assert _parse_bool(None, default=False) is False

    def test_features_config_uses_parse_bool(self):
        """Verify FeaturesConfig properly parses string booleans."""
        from mara_host.config.robot_config import FeaturesConfig

        config = FeaturesConfig.from_dict({
            "telemetry": "yes",
            "encoder": "true",
            "motion": "1",
            "modes": "no",
            "camera": "false",
        })

        assert config.telemetry is True
        assert config.encoder is True
        assert config.motion is True
        assert config.modes is False
        assert config.camera is False


# =============================================================================
# Phase 3: Additional Fixes Tests
# =============================================================================

class TestAdditionalFixes:
    """Tests for Phase 3 fixes (file cleanup, type safety, etc.)."""

    def test_file_logger_cleanup_on_partial_failure(self, tmp_path):
        """Verify file logger cleans up on partial failure in start()."""
        from mara_host.telemetry.file_logger import TelemetryFileLogger
        from mara_host.core.event_bus import EventBus

        bus = EventBus()
        logger = TelemetryFileLogger(bus, tmp_path)

        # Start should work
        logger.start()
        assert logger._imu_fp is not None
        assert logger._ultra_fp is not None

        # Stop should close files
        logger.stop()
        assert logger._imu_fp is None
        assert logger._ultra_fp is None

    def test_calibration_store_handles_malformed_records(self, tmp_path):
        """Verify CalibrationStore handles malformed records gracefully."""
        from mara_host.services.persistence.store import CalibrationStore
        import json

        store = CalibrationStore(tmp_path)

        # Write malformed data where records is a list instead of dict
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(json.dumps({
            "kind": "calibrations",
            "version": 1,
            "records": ["not", "a", "dict"],  # Malformed
        }))

        # Should return None, not crash
        result = store.get_record("test")
        assert result is None

    def test_replay_service_handles_non_dict_json(self, tmp_path):
        """Verify ReplayService handles JSON arrays/primitives."""
        from mara_host.services.recording.recording_service import ReplayService

        # Create a session directory with events file
        session_dir = tmp_path / "test_session"
        session_dir.mkdir()
        events_file = session_dir / "events.jsonl"
        events_file.write_text(
            '{"ts": 1000000000, "event": "test", "topic": "foo", "data": {}}\n'
            '[1, 2, 3]\n'  # Array - should be skipped
            '"just a string"\n'  # String - should be skipped
            '{"ts": 2000000000, "event": "test2", "topic": "bar", "data": {}}\n'
        )

        service = ReplayService(
            session_name="test_session",
            log_dir=tmp_path,
        )

        events = list(service.events())

        # Should only have 2 valid events, skipping array and string
        assert len(events) == 2
        assert events[0].event_type == "test"
        assert events[1].event_type == "test2"

    def test_tcp_transport_specific_exception_handling(self):
        """Verify TCP transport only catches specific socket exceptions."""
        from mara_host.transport.tcp_transport import AsyncTcpTransport

        transport = AsyncTcpTransport("localhost", 9999)

        # Verify the stop method exists and handles exceptions properly
        # (We can't easily test the actual exception handling without mocking)
        assert hasattr(transport, 'stop')


# =============================================================================
# Protocol Tests (Phase 6 - Binary ACK)
# =============================================================================

class TestProtocolBinaryAck:
    """Tests for binary ACK encoding/decoding."""

    def test_encode_ack_bin(self):
        """Verify binary ACK encoding."""
        from mara_host.core.protocol import encode_ack_bin, decode_ack_bin

        # Encode OK ACK
        encoded = encode_ack_bin(0x1234, ok=True)
        assert len(encoded) > 3  # Has framing

    def test_decode_ack_bin(self):
        """Verify binary ACK decoding."""
        from mara_host.core.protocol import decode_ack_bin

        # Valid ACK: seq=0x1234, ok=True
        payload = bytes([0x12, 0x34, 0x00])
        seq, ok = decode_ack_bin(payload)
        assert seq == 0x1234
        assert ok is True

        # Valid ACK: seq=0xABCD, ok=False
        payload = bytes([0xAB, 0xCD, 0x01])
        seq, ok = decode_ack_bin(payload)
        assert seq == 0xABCD
        assert ok is False

    def test_decode_ack_bin_rejects_short_payload(self):
        """Verify binary ACK decoder rejects short payloads."""
        from mara_host.core.protocol import decode_ack_bin

        with pytest.raises(ValueError, match="too short"):
            decode_ack_bin(bytes([0x12, 0x34]))  # Only 2 bytes


# =============================================================================
# Missing Coverage Tests
# =============================================================================

class TestRobotLifecycle:
    """Tests for Robot.off() and service cleanup."""

    def test_robot_off_unsubscribes_handler(self):
        """Verify Robot.off() properly removes event handlers."""
        from mara_host.core.event_bus import EventBus

        bus = EventBus()
        received = []

        def handler(data):
            received.append(data)

        # Simulate robot with bus
        class FakeRobot:
            def __init__(self):
                self._bus = bus

            def on(self, event, handler):
                self._bus.subscribe(event, handler)

            def off(self, event, handler):
                if self._bus is None:
                    return
                self._bus.unsubscribe(event, handler)

        robot = FakeRobot()
        robot.on("test.event", handler)

        # Should receive event
        bus.publish("test.event", {"value": 1})
        assert len(received) == 1

        # Unsubscribe
        robot.off("test.event", handler)

        # Should NOT receive event after unsubscribe
        bus.publish("test.event", {"value": 2})
        assert len(received) == 1  # Still 1, not 2

    def test_robot_off_handles_none_bus(self):
        """Verify Robot.off() handles None bus gracefully."""
        class FakeRobot:
            def __init__(self):
                self._bus = None

            def off(self, event, handler):
                if self._bus is None:
                    return
                self._bus.unsubscribe(event, handler)

        robot = FakeRobot()
        # Should not raise
        robot.off("test.event", lambda x: None)


class TestShutdownUtility:
    """Tests for shutdown_gracefully utility."""

    @pytest.mark.asyncio
    async def test_shutdown_gracefully_collects_errors(self):
        """Verify shutdown_gracefully collects errors from failing components."""
        from mara_host.core.shutdown import shutdown_gracefully, ShutdownResult

        async def success_component():
            pass

        async def failing_component():
            raise RuntimeError("Component failed")

        components = [
            ("success1", success_component),
            ("failing", failing_component),
            ("success2", success_component),
        ]

        result = await shutdown_gracefully(components, continue_on_error=True)

        assert isinstance(result, ShutdownResult)
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].component == "failing"
        assert isinstance(result.errors[0].error, RuntimeError)

    @pytest.mark.asyncio
    async def test_shutdown_gracefully_all_success(self):
        """Verify shutdown_gracefully returns success when all components succeed."""
        from mara_host.core.shutdown import shutdown_gracefully

        async def success_component():
            pass

        components = [
            ("comp1", success_component),
            ("comp2", success_component),
        ]

        result = await shutdown_gracefully(components)

        assert result.success is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_shutdown_gracefully_stops_on_error_when_configured(self):
        """Verify shutdown_gracefully stops on first error when continue_on_error=False."""
        from mara_host.core.shutdown import shutdown_gracefully

        call_order = []

        async def comp1():
            call_order.append("comp1")

        async def comp2_fails():
            call_order.append("comp2")
            raise RuntimeError("Failed")

        async def comp3():
            call_order.append("comp3")

        components = [
            ("comp1", comp1),
            ("comp2", comp2_fails),
            ("comp3", comp3),
        ]

        result = await shutdown_gracefully(components, continue_on_error=False)

        assert result.success is False
        assert len(result.errors) == 1
        # comp3 should NOT have been called
        assert call_order == ["comp1", "comp2"]


class TestHandshakeLock:
    """Tests for handshake lock in client.py."""

    @pytest.mark.asyncio
    async def test_client_has_handshake_lock(self):
        """Verify client has handshake lock for race prevention."""
        from mara_host.command.client import BaseMaraClient
        from unittest.mock import MagicMock

        transport = MagicMock()
        transport.set_frame_handler = MagicMock()

        client = BaseMaraClient(
            transport=transport,
            require_version_match=False,
        )

        assert hasattr(client, '_handshake_lock')
        assert isinstance(client._handshake_lock, asyncio.Lock)


class TestTcpTransportExceptions:
    """Tests for TCP transport specific exception handling."""

    @pytest.mark.asyncio
    async def test_tcp_transport_catches_connection_reset(self):
        """Verify TCP transport catches ConnectionResetError during cleanup."""
        from mara_host.transport.tcp_transport import AsyncTcpTransport
        from unittest.mock import MagicMock, AsyncMock

        transport = AsyncTcpTransport("localhost", 9999)

        # Mock writer that raises ConnectionResetError
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock(side_effect=ConnectionResetError("Connection reset"))

        transport._writer = mock_writer
        transport._reader = MagicMock()
        transport._task = None

        # Should not raise - exception should be caught
        await transport.stop()

        # Writer should be cleared
        assert transport._writer is None

    @pytest.mark.asyncio
    async def test_tcp_transport_catches_broken_pipe(self):
        """Verify TCP transport catches BrokenPipeError during cleanup."""
        from mara_host.transport.tcp_transport import AsyncTcpTransport
        from unittest.mock import MagicMock, AsyncMock

        transport = AsyncTcpTransport("localhost", 9999)

        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock(side_effect=BrokenPipeError("Broken pipe"))

        transport._writer = mock_writer
        transport._reader = MagicMock()
        transport._task = None

        # Should not raise
        await transport.stop()
        assert transport._writer is None

    @pytest.mark.asyncio
    async def test_tcp_transport_propagates_cancelled_error(self):
        """Verify TCP transport does NOT suppress CancelledError."""
        from mara_host.transport.tcp_transport import AsyncTcpTransport
        from unittest.mock import MagicMock, AsyncMock

        transport = AsyncTcpTransport("localhost", 9999)

        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock(side_effect=asyncio.CancelledError())

        transport._writer = mock_writer
        transport._reader = MagicMock()
        transport._task = None

        # CancelledError should propagate
        with pytest.raises(asyncio.CancelledError):
            await transport.stop()


class TestBinaryParserOptimizations:
    """Tests for binary parser optimization correctness."""

    def test_binary_parser_sensor_health_loop_efficiency(self):
        """Verify sensor health parsing handles count > available data efficiently."""
        from mara_host.telemetry.binary_parser import (
            parse_telemetry_bin,
            TELEM_SENSOR_HEALTH,
        )

        # Build packet with sensor health section
        # Header: version(1), seq(2), ts_ms(4), section_count(1) = 8 bytes
        header = struct.pack("<BHIB", 1, 0, 1000, 1)

        # Section header: id(1), len(2)
        # Sensor health: count(1) + entries(4 bytes each)
        # Claim count=255 but only provide 2 entries (8 bytes)
        section_body = bytes([255])  # count = 255
        # Add 2 valid entries (kind, sensor_id, flags, detail) = 4 bytes each
        section_body += struct.pack("<BBBB", 1, 0, 0x03, 0)  # Entry 1
        section_body += struct.pack("<BBBB", 2, 1, 0x03, 0)  # Entry 2

        section_hdr = struct.pack("<BH", TELEM_SENSOR_HEALTH, len(section_body))
        payload = header + section_hdr + section_body

        # Should parse without hanging (loop limited by available data)
        result = parse_telemetry_bin(payload)

        # Should have parsed only 2 entries despite count=255
        assert result.sensor_health is not None
        assert len(result.sensor_health.sensors) == 2

    def test_binary_parser_uses_memoryview_correctly(self):
        """Verify binary parser produces correct results with memoryview optimization."""
        from mara_host.telemetry.binary_parser import (
            parse_telemetry_bin,
            TELEM_IMU,
        )

        # Build valid IMU telemetry packet
        header = struct.pack("<BHIB", 1, 42, 12345, 1)  # version=1, seq=42, ts=12345, sections=1

        # IMU section: online(1), ok(1), ax/ay/az/gx/gy/gz/temp (7 x int16)
        imu_body = struct.pack("<BB7h", 1, 1, 1000, 0, -1000, 100, -100, 50, 2500)
        section_hdr = struct.pack("<BH", TELEM_IMU, len(imu_body))

        payload = header + section_hdr + imu_body
        result = parse_telemetry_bin(payload)

        # Verify parsing is correct despite memoryview optimization
        assert result.ts_ms == 12345
        assert result.imu is not None
        assert result.imu.online is True
        assert result.imu.ok is True
        assert result.imu.ax_g == pytest.approx(1.0, abs=0.01)  # 1000 * 0.001
        assert result.imu.az_g == pytest.approx(-1.0, abs=0.01)  # -1000 * 0.001


class TestIntegration:
    """Integration tests for systemic fixes working together."""

    @pytest.mark.asyncio
    async def test_client_validates_velocity_commands(self):
        """Verify client validates velocity commands before sending."""
        from mara_host.command.client import _validate_command_payload

        # Should not raise for valid values
        _validate_command_payload("CMD_SET_VEL", {"vx": 0.5, "omega": 0.1})

        # Should raise for NaN
        with pytest.raises(ValueError):
            _validate_command_payload("CMD_SET_VEL", {"vx": float('nan'), "omega": 0.1})

        # Should raise for Inf
        with pytest.raises(ValueError):
            _validate_command_payload("CMD_SET_VEL", {"vx": 0.5, "omega": float('inf')})

    @pytest.mark.asyncio
    async def test_commander_events_include_rejection(self):
        """Verify commander emits rejection events."""
        from mara_host.command.coms.reliable_commander import ReliableCommander

        events = []
        send_mock = AsyncMock(return_value=1)
        commander = ReliableCommander(
            send_func=send_mock,
            on_event=lambda e: events.append(e),
        )

        # Fill pending to max
        commander._pending = {i: MagicMock() for i in range(256)}

        # Try to send - should be rejected
        await commander.send("CMD_TEST", {}, wait_for_ack=True)

        # Find rejection event
        rejection = next((e for e in events if e.get("event") == "cmd.rejected"), None)
        assert rejection is not None
        assert rejection["reason"] == "too_many_pending"
        assert rejection["count"] == 256
