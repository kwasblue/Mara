# tests/test_gui_panels.py
"""Tests for GUI panels and components.

These tests verify that GUI components can be instantiated and their
basic functionality works correctly with mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass


# ============== Fixtures ==============


@pytest.fixture
def mock_signals():
    """Create mock GuiSignals."""
    signals = MagicMock()
    signals.connection_changed = MagicMock()
    signals.connection_changed.connect = MagicMock()
    signals.connection_changed.emit = MagicMock()

    signals.state_changed = MagicMock()
    signals.state_changed.connect = MagicMock()
    signals.state_changed.emit = MagicMock()

    signals.capabilities_changed = MagicMock()
    signals.capabilities_changed.connect = MagicMock()

    signals.status_message = MagicMock()
    signals.status_message.emit = MagicMock()

    signals.status_error = MagicMock()
    signals.status_error.emit = MagicMock()

    signals.log_info = MagicMock()
    signals.log_error = MagicMock()
    signals.log_warning = MagicMock()

    signals.encoder_data = MagicMock()
    signals.encoder_data.connect = MagicMock()

    signals.imu_data = MagicMock()
    signals.imu_data.connect = MagicMock()

    return signals


@pytest.fixture
def mock_controller():
    """Create mock RobotController."""
    controller = MagicMock()
    controller.is_connected = False
    controller._running = False
    controller._loop = None
    controller._connection_service = None

    # State
    controller.state = MagicMock()
    controller.state.is_connected = False
    controller.state.transport_config = MagicMock()
    controller.state.transport_config.port = "/dev/ttyUSB0"
    controller.state.transport_config.baudrate = 115200

    # Motor PID
    controller.enable_velocity_pid = MagicMock()
    controller.set_velocity_gains = MagicMock()
    controller.set_velocity_target = MagicMock()

    # Stepper
    controller.stepper_move = MagicMock()
    controller.stepper_stop = MagicMock()
    controller.stepper_enable = MagicMock()

    # Encoder
    controller.encoder_attach = MagicMock()
    controller.encoder_reset = MagicMock()
    controller.encoder_read = MagicMock()

    # Ultrasonic
    controller.ultrasonic_attach = MagicMock()
    controller.ultrasonic_read = MagicMock()

    # Motor/Servo
    controller.set_motor_speed = MagicMock()
    controller.stop_motor = MagicMock()
    controller.set_servo_angle = MagicMock()
    controller.set_servo_angle_reliable = MagicMock()

    # Signal bus
    controller.signal_define = MagicMock()
    controller.signal_set = MagicMock()
    controller.signal_get = MagicMock()
    controller.signals_list = MagicMock()
    controller.signals_clear = MagicMock()
    controller.signal_delete = MagicMock()

    # Controllers
    controller.controller_config = MagicMock()
    controller.controller_enable = MagicMock()
    controller.controller_set_param = MagicMock()
    controller.controller_reset = MagicMock()

    # Observers
    controller.observer_config = MagicMock()
    controller.observer_enable = MagicMock()
    controller.observer_set_param_array = MagicMock()
    controller.observer_reset = MagicMock()

    # State control
    controller.arm = MagicMock()
    controller.disarm = MagicMock()
    controller.estop = MagicMock()
    controller.clear_estop = MagicMock()

    # GPIO
    controller.gpio_write = MagicMock()

    return controller


@pytest.fixture
def mock_settings():
    """Create mock GuiSettings."""
    settings = MagicMock()
    settings.get_max_linear_velocity = MagicMock(return_value=1.0)
    settings.get_max_angular_velocity = MagicMock(return_value=2.0)
    settings.set_max_linear_velocity = MagicMock()
    settings.set_max_angular_velocity = MagicMock()
    return settings


# ============== Controller Method Tests ==============


class TestRobotControllerMethods:
    """Tests for RobotController new methods."""

    def test_motor_pid_methods_exist(self, mock_controller):
        """Verify motor PID methods are callable."""
        mock_controller.enable_velocity_pid(0, True)
        mock_controller.enable_velocity_pid.assert_called_once_with(0, True)

        mock_controller.set_velocity_gains(0, 1.0, 0.1, 0.01)
        mock_controller.set_velocity_gains.assert_called_once_with(0, 1.0, 0.1, 0.01)

        mock_controller.set_velocity_target(0, 10.0)
        mock_controller.set_velocity_target.assert_called_once_with(0, 10.0)

    def test_stepper_methods_exist(self, mock_controller):
        """Verify stepper motor methods are callable."""
        mock_controller.stepper_move(0, 200, 500.0)
        mock_controller.stepper_move.assert_called_once_with(0, 200, 500.0)

        mock_controller.stepper_stop(0)
        mock_controller.stepper_stop.assert_called_once_with(0)

        mock_controller.stepper_enable(0, True)
        mock_controller.stepper_enable.assert_called_once_with(0, True)

    def test_encoder_methods_exist(self, mock_controller):
        """Verify encoder methods are callable."""
        mock_controller.encoder_attach(0, 32, 33)
        mock_controller.encoder_attach.assert_called_once_with(0, 32, 33)

        mock_controller.encoder_reset(0)
        mock_controller.encoder_reset.assert_called_once_with(0)

    def test_ultrasonic_methods_exist(self, mock_controller):
        """Verify ultrasonic methods are callable."""
        mock_controller.ultrasonic_attach(0)
        mock_controller.ultrasonic_attach.assert_called_once_with(0)

        mock_controller.ultrasonic_read(0)
        mock_controller.ultrasonic_read.assert_called_once_with(0)

    def test_signal_bus_methods_exist(self, mock_controller):
        """Verify signal bus methods are callable."""
        mock_controller.signal_define(0, "test_signal", "REF", 0.0)
        mock_controller.signal_define.assert_called_once_with(0, "test_signal", "REF", 0.0)

        mock_controller.signal_set(0, 1.0)
        mock_controller.signal_set.assert_called_once_with(0, 1.0)

        mock_controller.signals_clear()
        mock_controller.signals_clear.assert_called_once()

    def test_controller_slot_methods_exist(self, mock_controller):
        """Verify controller slot methods are callable."""
        config = {"type": "pid", "kp": 1.0, "ki": 0.1, "kd": 0.01}
        mock_controller.controller_config(0, config)
        mock_controller.controller_config.assert_called_once_with(0, config)

        mock_controller.controller_enable(0, True)
        mock_controller.controller_enable.assert_called_once_with(0, True)

        mock_controller.controller_reset(0)
        mock_controller.controller_reset.assert_called_once_with(0)

    def test_observer_slot_methods_exist(self, mock_controller):
        """Verify observer slot methods are callable."""
        config = {"n_states": 2, "n_inputs": 1, "n_outputs": 1}
        mock_controller.observer_config(0, config)
        mock_controller.observer_config.assert_called_once_with(0, config)

        mock_controller.observer_enable(0, True)
        mock_controller.observer_enable.assert_called_once_with(0, True)

        mock_controller.observer_set_param_array(0, "L", [0.5, 0.5])
        mock_controller.observer_set_param_array.assert_called_once_with(0, "L", [0.5, 0.5])


# ============== Test Service Tests ==============


class TestTestService:
    """Tests for TestService integration."""

    @pytest.fixture
    def mock_client(self):
        """Create mock MaraClient for TestService."""
        client = MagicMock()
        client.firmware_version = "1.0.0"
        client.protocol_version = 1
        client.features = ["dc_motor", "servo"]
        client.bus = MagicMock()
        client.bus.subscribe = MagicMock()
        client.send_ping = AsyncMock()
        client.cmd_arm = AsyncMock(return_value=(True, None))
        client.cmd_disarm = AsyncMock(return_value=(True, None))
        client.cmd_activate = AsyncMock(return_value=(True, None))
        client.cmd_deactivate = AsyncMock(return_value=(True, None))
        client.cmd_led_on = AsyncMock(return_value=(True, None))
        client.cmd_led_off = AsyncMock(return_value=(True, None))
        client.cmd_dc_motor_set = AsyncMock(return_value=(True, None))
        client.cmd_servo_attach = AsyncMock(return_value=(True, None))
        client.cmd_servo_set_angle = AsyncMock(return_value=(True, None))
        client.cmd_servo_detach = AsyncMock(return_value=(True, None))
        client.cmd_gpio_mode = AsyncMock(return_value=(True, None))
        client.cmd_gpio_write = AsyncMock(return_value=(True, None))
        return client

    @pytest.mark.asyncio
    async def test_test_connection(self, mock_client):
        """Test connection test."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        result = await service.test_connection()

        assert result.status == TestStatus.PASSED
        assert result.name == "Connection"
        assert "firmware" in result.details

    @pytest.mark.asyncio
    async def test_test_arm_disarm(self, mock_client):
        """Test arm/disarm test."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        result = await service.test_arm_disarm()

        assert result.status == TestStatus.PASSED
        mock_client.cmd_arm.assert_called()
        mock_client.cmd_disarm.assert_called()

    @pytest.mark.asyncio
    async def test_test_led(self, mock_client):
        """Test LED test."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        result = await service.test_led()

        assert result.status == TestStatus.PASSED
        mock_client.cmd_led_on.assert_called()
        mock_client.cmd_led_off.assert_called()

    @pytest.mark.asyncio
    async def test_test_motors(self, mock_client):
        """Test motor test."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        result = await service.test_motors(motor_ids=[0, 1])

        assert result.status == TestStatus.PASSED
        assert mock_client.cmd_dc_motor_set.call_count >= 2  # At least 2 motors

    @pytest.mark.asyncio
    async def test_test_servos(self, mock_client):
        """Test servo test."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        result = await service.test_servos(servo_ids=[0])

        assert result.status == TestStatus.PASSED
        mock_client.cmd_servo_attach.assert_called()
        mock_client.cmd_servo_set_angle.assert_called()
        mock_client.cmd_servo_detach.assert_called()

    @pytest.mark.asyncio
    async def test_test_gpio(self, mock_client):
        """Test GPIO test."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        result = await service.test_gpio(pin=2)

        assert result.status == TestStatus.PASSED
        mock_client.cmd_gpio_mode.assert_called()
        mock_client.cmd_gpio_write.assert_called()

    @pytest.mark.asyncio
    async def test_run_tests(self, mock_client):
        """Test running specific tests."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        results = await service.run_tests(["connection", "led"])

        assert len(results) == 2
        assert all(r.status == TestStatus.PASSED for r in results)

    @pytest.mark.asyncio
    async def test_run_unknown_test(self, mock_client):
        """Test running unknown test returns skipped."""
        from mara_host.services.testing.test_service import TestService, TestStatus

        service = TestService(mock_client)
        results = await service.run_tests(["unknown_test"])

        assert len(results) == 1
        assert results[0].status == TestStatus.SKIPPED


# ============== Calibration Tests ==============


class TestCalibrationResult:
    """Tests for calibration result handling."""

    def test_calibration_result_structure(self):
        """Test CalibrationResult dataclass."""
        from mara_host.gui.panels.calibration import CalibrationResult

        result = CalibrationResult(
            wizard_type="motor",
            success=True,
            message="Calibration complete",
            data={"dead_zone": 15, "inverted": False}
        )

        assert result.wizard_type == "motor"
        assert result.success is True
        assert result.data["dead_zone"] == 15


class TestCalibrationState:
    """Tests for CalibrationState enum."""

    def test_calibration_states(self):
        """Test CalibrationState values."""
        from mara_host.gui.panels.calibration import CalibrationState

        assert CalibrationState.IDLE.value == "idle"
        assert CalibrationState.RUNNING.value == "running"
        assert CalibrationState.WAITING_USER.value == "waiting_user"
        assert CalibrationState.COMPLETED.value == "completed"
        assert CalibrationState.CANCELLED.value == "cancelled"


# ============== Session Recording Tests ==============


class TestRecordingService:
    """Tests for RecordingService."""

    def test_recording_config(self):
        """Test RecordingConfig dataclass."""
        from mara_host.services.recording.recording_service import RecordingConfig
        from pathlib import Path

        config = RecordingConfig(
            session_name="test_session",
            log_dir=Path("/tmp/logs"),
            serial_port="/dev/ttyUSB0",
            baudrate=115200,
            duration_s=10.0
        )

        assert config.session_name == "test_session"
        assert config.duration_s == 10.0

    def test_session_info(self):
        """Test SessionInfo dataclass."""
        from mara_host.services.recording.recording_service import SessionInfo
        from pathlib import Path

        info = SessionInfo(
            name="test",
            path=Path("/tmp/test"),
            event_count=100,
            duration_s=5.0,
            topics=["telemetry", "state"]
        )

        assert info.name == "test"
        assert info.event_count == 100
        assert len(info.topics) == 2


class TestReplayService:
    """Tests for ReplayService."""

    def test_list_sessions_empty(self, tmp_path):
        """Test listing sessions in empty directory."""
        from mara_host.services.recording.recording_service import ReplayService

        sessions = ReplayService.list_sessions(tmp_path)
        assert sessions == []

    def test_list_sessions_with_sessions(self, tmp_path):
        """Test listing sessions with existing sessions."""
        from mara_host.services.recording.recording_service import ReplayService
        import json

        # Create fake sessions
        session1 = tmp_path / "session1"
        session1.mkdir()
        (session1 / "events.jsonl").write_text('{"ts": 0, "event": "test"}\n')

        session2 = tmp_path / "session2"
        session2.mkdir()
        (session2 / "events.jsonl").write_text('{"ts": 0, "event": "test"}\n')

        sessions = ReplayService.list_sessions(tmp_path)
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions

    def test_get_session_info(self, tmp_path):
        """Test getting session info."""
        from mara_host.services.recording.recording_service import ReplayService
        import json

        # Create fake session
        session = tmp_path / "test_session"
        session.mkdir()

        events = [
            {"ts": 1000000000, "event": "telemetry", "topic": "state"},
            {"ts": 2000000000, "event": "telemetry", "topic": "imu"},
            {"ts": 3000000000, "event": "telemetry", "topic": "state"},
        ]
        with open(session / "events.jsonl", "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        service = ReplayService("test_session", tmp_path)
        info = service.get_session_info()

        assert info is not None
        assert info.name == "test_session"
        assert info.event_count == 3
        assert "state" in info.topics
        assert "imu" in info.topics


# ============== DeviceCapabilities Tests ==============


class TestDeviceCapabilities:
    """Tests for DeviceCapabilities."""

    def test_has_features(self):
        """Test feature checking."""
        from mara_host.gui.core.state import DeviceCapabilities

        caps = DeviceCapabilities(
            features=["dc_motor", "servo", "encoder", "gpio"],
            capabilities_mask=0
        )

        assert caps.has_dc_motor is True
        assert caps.has_servo is True
        assert caps.has_encoder is True
        assert caps.has_gpio is True
        assert caps.has_stepper is False
        assert caps.has_imu is False

    def test_has_any_motor(self):
        """Test any motor check."""
        from mara_host.gui.core.state import DeviceCapabilities

        caps_with_dc = DeviceCapabilities(features=["dc_motor"])
        caps_with_stepper = DeviceCapabilities(features=["stepper"])
        caps_with_servo = DeviceCapabilities(features=["servo"])
        caps_without = DeviceCapabilities(features=["gpio"])

        assert caps_with_dc.has_any_motor is True
        assert caps_with_stepper.has_any_motor is True
        assert caps_with_servo.has_any_motor is True
        assert caps_without.has_any_motor is False

    def test_summary(self):
        """Test capabilities summary."""
        from mara_host.gui.core.state import DeviceCapabilities

        caps = DeviceCapabilities(features=["dc_motor", "servo"])
        summary = caps.summary()

        assert "dc_motor" in summary
        assert "servo" in summary

    def test_empty_features(self):
        """Test with no features."""
        from mara_host.gui.core.state import DeviceCapabilities

        caps = DeviceCapabilities()

        assert caps.has_dc_motor is False
        assert caps.has_any_motor is False
        assert caps.summary() == "No features reported"


# ============== GuiSignals Tests ==============


class TestGuiSignals:
    """Tests for GuiSignals."""

    def test_signals_exist(self):
        """Test that all required signals exist."""
        from mara_host.gui.core.signals import GuiSignals

        signals = GuiSignals()

        # Connection
        assert hasattr(signals, 'connection_changed')
        assert hasattr(signals, 'connection_error')

        # State
        assert hasattr(signals, 'state_changed')
        assert hasattr(signals, 'capabilities_changed')

        # Telemetry
        assert hasattr(signals, 'telemetry_received')
        assert hasattr(signals, 'imu_data')
        assert hasattr(signals, 'encoder_data')

        # New signals
        assert hasattr(signals, 'calibration_started')
        assert hasattr(signals, 'calibration_progress')
        assert hasattr(signals, 'calibration_result')
        assert hasattr(signals, 'test_started')
        assert hasattr(signals, 'test_result')
        assert hasattr(signals, 'recording_started')
        assert hasattr(signals, 'recording_stopped')
        assert hasattr(signals, 'replay_started')
        assert hasattr(signals, 'replay_stopped')
        assert hasattr(signals, 'signals_updated')
        assert hasattr(signals, 'controller_status_updated')
        assert hasattr(signals, 'observer_status_updated')

    def test_log_helpers(self):
        """Test log helper methods."""
        from mara_host.gui.core.signals import GuiSignals
        from unittest.mock import patch

        signals = GuiSignals()

        with patch.object(signals, 'log_message') as mock_log:
            mock_log.emit = MagicMock()
            signals.log_info("Test message")
            mock_log.emit.assert_called_once()
            args = mock_log.emit.call_args[0]
            assert args[1] == "INFO"
            assert args[2] == "Test message"


# ============== Integration Import Tests ==============


class TestPanelImports:
    """Test that all panels can be imported."""

    def test_import_control_panel(self):
        """Test ControlPanel import."""
        from mara_host.gui.panels.control import ControlPanel
        assert ControlPanel is not None

    def test_import_testing_panel(self):
        """Test TestingPanel import."""
        from mara_host.gui.panels.testing import TestingPanel
        assert TestingPanel is not None

    def test_import_calibration_panel(self):
        """Test CalibrationPanel import."""
        from mara_host.gui.panels.calibration import CalibrationPanel
        assert CalibrationPanel is not None

    def test_import_advanced_panel(self):
        """Test AdvancedPanel import."""
        from mara_host.gui.panels.advanced import AdvancedPanel
        assert AdvancedPanel is not None

    def test_import_session_panel(self):
        """Test SessionPanel import."""
        from mara_host.gui.panels.session import SessionPanel
        assert SessionPanel is not None

    def test_import_all_panels(self):
        """Test all panels can be imported from __init__."""
        from mara_host.gui.panels import (
            DashboardPanel,
            ControlPanel,
            CameraPanel,
            CommandsPanel,
            CalibrationPanel,
            TestingPanel,
            AdvancedPanel,
            SessionPanel,
            PinoutPanel,
            FirmwarePanel,
            ConfigPanel,
            LogsPanel,
        )

        assert DashboardPanel is not None
        assert ControlPanel is not None
        assert CalibrationPanel is not None
        assert TestingPanel is not None
        assert AdvancedPanel is not None
        assert SessionPanel is not None


class TestMainWindowPanels:
    """Test MainWindow panel configuration."""

    def test_panel_definitions(self):
        """Test MainWindow PANELS list."""
        from mara_host.gui.main_window import MainWindow

        panel_ids = [p[0] for p in MainWindow.PANELS]

        # Check all expected panels are present
        assert "dashboard" in panel_ids
        assert "control" in panel_ids
        assert "camera" in panel_ids
        assert "commands" in panel_ids
        assert "calibration" in panel_ids
        assert "testing" in panel_ids
        assert "advanced" in panel_ids
        assert "session" in panel_ids
        assert "pinout" in panel_ids
        assert "firmware" in panel_ids
        assert "config" in panel_ids
        assert "logs" in panel_ids

        # Check count
        assert len(MainWindow.PANELS) == 12
