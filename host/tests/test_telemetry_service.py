# tests/test_telemetry_service.py
"""Tests for TelemetryService."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import time

from mara_host.services.telemetry import (
    TelemetryService,
    TelemetrySnapshot,
    ImuData,
    EncoderData,
)


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self._handlers = {}

    def subscribe(self, topic: str, handler):
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler):
        if topic in self._handlers:
            self._handlers[topic] = [h for h in self._handlers[topic] if h != handler]

    def publish(self, topic: str, data):
        for handler in self._handlers.get(topic, []):
            handler(data)


class TestImuData:
    """Tests for ImuData dataclass."""

    def test_default_values(self):
        imu = ImuData()
        assert imu.ax == 0.0
        assert imu.ay == 0.0
        assert imu.az == 0.0
        assert imu.gx == 0.0
        assert imu.gy == 0.0
        assert imu.gz == 0.0

    def test_from_dict(self):
        data = {
            "ax": 0.1,
            "ay": 0.2,
            "az": 9.8,
            "gx": 0.01,
            "gy": 0.02,
            "gz": 0.03,
        }
        imu = ImuData.from_dict(data)

        assert imu.ax == 0.1
        assert imu.ay == 0.2
        assert imu.az == 9.8
        assert imu.gx == 0.01
        assert imu.gy == 0.02
        assert imu.gz == 0.03

    def test_from_dict_missing_keys(self):
        data = {"ax": 1.0}  # Missing most keys
        imu = ImuData.from_dict(data)

        assert imu.ax == 1.0
        assert imu.ay == 0.0  # Default


class TestEncoderData:
    """Tests for EncoderData dataclass."""

    def test_from_dict(self):
        data = {"ticks": 1000, "velocity": 5.2}
        enc = EncoderData.from_dict(encoder_id=0, data=data)

        assert enc.encoder_id == 0
        assert enc.ticks == 1000
        assert enc.velocity == 5.2


class TestTelemetryService:
    """Tests for TelemetryService."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client with event bus."""
        client = MagicMock()
        client.bus = MockEventBus()
        client.send_reliable = AsyncMock(return_value=(True, None))
        return client

    @pytest.fixture
    def telemetry_service(self, mock_client):
        """Create TelemetryService."""
        return TelemetryService(mock_client, history_size=50)

    @pytest.mark.asyncio
    async def test_start_subscribes_to_topics(self, telemetry_service, mock_client):
        """Test that start subscribes to telemetry topics."""
        await telemetry_service.start(interval_ms=100)

        # Check that interval was set
        mock_client.send_reliable.assert_called_once_with(
            "CMD_TELEM_SET_INTERVAL", {"interval_ms": 100}
        )

        # Check subscriptions exist
        assert "telemetry.binary" in mock_client.bus._handlers
        assert "telemetry" in mock_client.bus._handlers
        assert "state.changed" in mock_client.bus._handlers

    def test_stop_unsubscribes(self, telemetry_service, mock_client):
        """Test that stop unsubscribes from topics."""
        # Manually set up subscribed state
        telemetry_service._subscribed = True
        mock_client.bus._handlers = {
            "telemetry.binary": [telemetry_service._on_binary_telemetry],
            "telemetry": [telemetry_service._on_json_telemetry],
            "state.changed": [telemetry_service._on_state_changed],
        }

        telemetry_service.stop()

        assert telemetry_service._subscribed is False

    def test_imu_callback_registration(self, telemetry_service):
        """Test IMU callback registration."""
        callback = MagicMock()
        telemetry_service.on_imu(callback)

        assert callback in telemetry_service._imu_callbacks

    def test_json_telemetry_updates_imu(self, telemetry_service, mock_client):
        """Test JSON telemetry updates IMU data."""
        callback = MagicMock()
        telemetry_service.on_imu(callback)

        # Simulate telemetry
        telemetry_data = {
            "imu": {
                "ax": 0.5,
                "ay": -0.3,
                "az": 9.8,
                "gx": 0.01,
                "gy": 0.02,
                "gz": 0.03,
            }
        }
        telemetry_service._on_json_telemetry(telemetry_data)

        # Check data was stored
        imu = telemetry_service.get_latest_imu()
        assert imu is not None
        assert imu.ax == 0.5
        assert imu.ay == -0.3
        assert imu.az == 9.8

        # Check callback was called
        callback.assert_called_once()
        call_arg = callback.call_args[0][0]
        assert call_arg.ax == 0.5

    def test_json_telemetry_updates_encoders(self, telemetry_service):
        """Test JSON telemetry updates encoder data."""
        callback = MagicMock()
        telemetry_service.on_encoder(callback)

        telemetry_data = {
            "encoder0": {"ticks": 100, "velocity": 1.5},
            "encoder1": {"ticks": -50, "velocity": -0.8},
        }
        telemetry_service._on_json_telemetry(telemetry_data)

        enc0 = telemetry_service.get_latest_encoder(0)
        enc1 = telemetry_service.get_latest_encoder(1)

        assert enc0.ticks == 100
        assert enc0.velocity == 1.5
        assert enc1.ticks == -50
        assert enc1.velocity == -0.8

        # Callback called twice (once per encoder)
        assert callback.call_count == 2

    def test_state_change_callback(self, telemetry_service):
        """Test state change callback."""
        callback = MagicMock()
        telemetry_service.on_state(callback)

        telemetry_service._on_state_changed({"state": "ARMED"})

        assert telemetry_service.get_state() == "ARMED"
        callback.assert_called_once_with("ARMED")

    def test_state_change_only_fires_on_change(self, telemetry_service):
        """Test state callback only fires on actual change."""
        callback = MagicMock()
        telemetry_service.on_state(callback)

        telemetry_service._on_state_changed({"state": "ARMED"})
        telemetry_service._on_state_changed({"state": "ARMED"})  # Same state

        # Should only fire once
        callback.assert_called_once()

    def test_get_snapshot(self, telemetry_service):
        """Test getting complete telemetry snapshot."""
        # Add some data
        telemetry_service._on_json_telemetry(
            {
                "imu": {"ax": 1.0, "ay": 2.0, "az": 3.0},
                "encoder0": {"ticks": 100, "velocity": 1.0},
            }
        )
        telemetry_service._on_state_changed({"state": "ACTIVE"})

        snapshot = telemetry_service.get_snapshot()

        assert isinstance(snapshot, TelemetrySnapshot)
        assert snapshot.state == "ACTIVE"
        assert snapshot.imu is not None
        assert snapshot.imu.ax == 1.0
        assert len(snapshot.encoders) == 1
        assert snapshot.encoders[0].ticks == 100

    def test_imu_history(self, telemetry_service):
        """Test IMU history tracking."""
        for i in range(5):
            telemetry_service._on_json_telemetry({"imu": {"ax": float(i)}})

        history = telemetry_service.get_imu_history()
        assert len(history) == 5
        assert history[0].ax == 0.0  # Oldest
        assert history[-1].ax == 4.0  # Newest

        # Get subset
        recent = telemetry_service.get_imu_history(count=3)
        assert len(recent) == 3
        assert recent[0].ax == 2.0

    def test_encoder_history(self, telemetry_service):
        """Test encoder history tracking."""
        for i in range(5):
            telemetry_service._on_json_telemetry(
                {"encoder0": {"ticks": i * 100, "velocity": float(i)}}
            )

        history = telemetry_service.get_encoder_history(0)
        assert len(history) == 5
        assert history[0].ticks == 0
        assert history[-1].ticks == 400

    def test_history_limit(self, telemetry_service):
        """Test history buffer limits."""
        # History size is 50
        for i in range(100):
            telemetry_service._on_json_telemetry({"imu": {"ax": float(i)}})

        history = telemetry_service.get_imu_history()
        assert len(history) == 50  # Limited to history_size
        assert history[0].ax == 50.0  # Oldest kept

    def test_get_all_encoders(self, telemetry_service):
        """Test getting all encoder data."""
        telemetry_service._on_json_telemetry(
            {
                "encoder0": {"ticks": 100},
                "encoder1": {"ticks": 200},
                "encoder2": {"ticks": 300},
            }
        )

        all_enc = telemetry_service.get_all_encoders()
        assert len(all_enc) == 3
        assert 0 in all_enc
        assert 1 in all_enc
        assert 2 in all_enc

    def test_raw_callback(self, telemetry_service):
        """Test raw telemetry callback."""
        callback = MagicMock()
        telemetry_service.on_raw(callback)

        data = {"custom": "data", "value": 42}
        telemetry_service._on_json_telemetry(data)

        callback.assert_called_once_with(data)

    def test_remove_callback(self, telemetry_service):
        """Test removing callbacks."""
        callback = MagicMock()
        telemetry_service.on_imu(callback)
        telemetry_service.remove_callback(callback)

        telemetry_service._on_json_telemetry({"imu": {"ax": 1.0}})

        callback.assert_not_called()

    def test_callback_exception_doesnt_break_service(self, telemetry_service):
        """Test that callback exceptions don't break the service."""
        bad_callback = MagicMock(side_effect=Exception("Callback error"))
        good_callback = MagicMock()

        telemetry_service.on_imu(bad_callback)
        telemetry_service.on_imu(good_callback)

        # Should not raise
        telemetry_service._on_json_telemetry({"imu": {"ax": 1.0}})

        # Good callback should still be called
        good_callback.assert_called_once()

    def test_binary_telemetry_with_mock_packet(self, telemetry_service):
        """Test binary telemetry handling."""

        class MockImu:
            ax = 1.0
            ay = 2.0
            az = 9.8
            gx = 0.1
            gy = 0.2
            gz = 0.3

        class MockEncoder:
            ticks = 500
            velocity = 2.5

        class MockPacket:
            imu = MockImu()
            encoders = [MockEncoder(), MockEncoder()]
            state = "ACTIVE"

        callback = MagicMock()
        telemetry_service.on_imu(callback)

        telemetry_service._on_binary_telemetry(MockPacket())

        imu = telemetry_service.get_latest_imu()
        assert imu.ax == 1.0
        assert imu.az == 9.8

        enc0 = telemetry_service.get_latest_encoder(0)
        assert enc0.ticks == 500

        assert telemetry_service.get_state() == "ACTIVE"
        callback.assert_called_once()

    def test_binary_telemetry_with_real_packet_shape(self, telemetry_service):
        """Test binary telemetry handling with current parser field names."""

        class RealImu:
            ax_g = 0.12
            ay_g = -0.34
            az_g = 1.01
            gx_dps = 4.5
            gy_dps = -5.5
            gz_dps = 6.5

        class RealEncoder0:
            encoder_id = 0
            ticks = 1234

        class RealPacket:
            imu = RealImu()
            encoder0 = RealEncoder0()

        telemetry_service._on_binary_telemetry(RealPacket())

        imu = telemetry_service.get_latest_imu()
        assert imu.ax == 0.12
        assert imu.ay == -0.34
        assert imu.gz == 6.5

        enc0 = telemetry_service.get_latest_encoder(0)
        assert enc0.ticks == 1234

    def test_json_telemetry_with_nested_firmware_shape(self, telemetry_service):
        """Test JSON telemetry handling with current firmware nested data shape."""
        telemetry_service._on_json_telemetry({
            "src": "mcu",
            "type": "TELEMETRY",
            "ts_ms": 123,
            "data": {
                "mode": {"state": "IDLE"},
                "imu": {
                    "ax_g": 0.5,
                    "ay_g": 0.0,
                    "az_g": 1.0,
                    "gx_dps": 1.5,
                    "gy_dps": 2.5,
                    "gz_dps": 3.5,
                },
                "encoder0": {"ticks": 77},
            },
        })

        imu = telemetry_service.get_latest_imu()
        assert imu.ax == 0.5
        assert imu.gx == 1.5
        assert telemetry_service.get_state() == "IDLE"

        enc0 = telemetry_service.get_latest_encoder(0)
        assert enc0.ticks == 77


class TestTelemetrySnapshot:
    """Tests for TelemetrySnapshot dataclass."""

    def test_default_values(self):
        snapshot = TelemetrySnapshot()
        assert snapshot.state == "UNKNOWN"
        assert snapshot.imu is None
        assert snapshot.encoders == []
        assert snapshot.motors == []

    def test_with_data(self):
        imu = ImuData(ax=1.0)
        enc = EncoderData(encoder_id=0, ticks=100)

        snapshot = TelemetrySnapshot(
            timestamp=time.time(),
            state="ACTIVE",
            imu=imu,
            encoders=[enc],
        )

        assert snapshot.state == "ACTIVE"
        assert snapshot.imu.ax == 1.0
        assert len(snapshot.encoders) == 1
