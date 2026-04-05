"""Tests for Linux runtime (linux_runtime.py)."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from mara_host.runtime.linux_runtime import (
    LinuxRuntime,
    LinuxRuntimeConfig,
    LinuxRuntimeState,
    ImuData,
)
from mara_host.bindings.mara_bindings import MaraState, MaraError, MaraBindingsError


class TestLinuxRuntimeConfig:
    """Tests for LinuxRuntimeConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LinuxRuntimeConfig()
        assert config.library_path is None
        assert config.gpio_chip == "/dev/gpiochip0"
        assert config.i2c_bus == 1
        assert config.pwm_chip == 0
        assert config.log_level == "info"
        assert config.auto_arm is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = LinuxRuntimeConfig(
            library_path="/custom/path/libmara.so",
            gpio_chip="/dev/gpiochip1",
            i2c_bus=2,
            auto_arm=True,
        )
        assert config.library_path == "/custom/path/libmara.so"
        assert config.gpio_chip == "/dev/gpiochip1"
        assert config.i2c_bus == 2
        assert config.auto_arm is True


class TestImuData:
    """Tests for ImuData dataclass."""

    def test_default_values(self):
        """Test default IMU data values."""
        imu = ImuData()
        assert imu.ax_g == 0.0
        assert imu.ay_g == 0.0
        assert imu.az_g == 0.0
        assert imu.gx_dps == 0.0
        assert imu.gy_dps == 0.0
        assert imu.gz_dps == 0.0
        assert imu.timestamp is not None

    def test_custom_values(self):
        """Test custom IMU data values."""
        ts = datetime.now()
        imu = ImuData(
            ax_g=0.1, ay_g=0.2, az_g=1.0,
            gx_dps=1.0, gy_dps=2.0, gz_dps=3.0,
            timestamp=ts,
        )
        assert imu.ax_g == 0.1
        assert imu.ay_g == 0.2
        assert imu.az_g == 1.0
        assert imu.gx_dps == 1.0
        assert imu.gy_dps == 2.0
        assert imu.gz_dps == 3.0
        assert imu.timestamp == ts


class TestLinuxRuntime:
    """Tests for LinuxRuntime."""

    @pytest.fixture
    def mock_bindings(self):
        """Create mock bindings."""
        bindings = MagicMock()
        bindings.create.return_value = MagicMock()  # Handle
        bindings.init.return_value = None
        bindings.start.return_value = None
        bindings.stop.return_value = None
        bindings.destroy.return_value = None
        bindings.arm.return_value = None
        bindings.disarm.return_value = None
        bindings.activate.return_value = None
        bindings.deactivate.return_value = None
        bindings.estop.return_value = None
        bindings.clear_estop.return_value = None
        bindings.get_state.return_value = MaraState.IDLE
        bindings.version.return_value = "1.0.0"
        bindings.get_identity.return_value = '{"version": "1.0.0"}'
        bindings.get_health.return_value = '{"healthy": true}'
        bindings.servo_attach.return_value = None
        bindings.servo_write.return_value = None
        bindings.servo_read.return_value = 90.0
        bindings.motor_set.return_value = None
        bindings.motor_stop.return_value = None
        bindings.motor_stop_all.return_value = None
        bindings.set_velocity.return_value = None
        bindings.stop_motion.return_value = None
        bindings.gpio_mode.return_value = None
        bindings.gpio_write.return_value = None
        bindings.gpio_read.return_value = True
        bindings.imu_read.return_value = ((0.0, 0.0, 1.0), (0.0, 0.0, 0.0))
        bindings.encoder_read.return_value = 1234
        return bindings

    @pytest.fixture
    def runtime(self, mock_bindings):
        """Create runtime with mocked bindings."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            rt = LinuxRuntime(library_path="/mock/libmara.so")
            return rt

    # =========================================================================
    # Lifecycle Tests
    # =========================================================================

    def test_initial_state(self):
        """Test initial runtime state."""
        rt = LinuxRuntime()
        assert rt.runtime_state == LinuxRuntimeState.CREATED
        assert rt.robot_state == MaraState.UNKNOWN
        assert not rt.is_connected
        assert not rt.is_armed

    @pytest.mark.asyncio
    async def test_start_transitions_to_started(self, runtime, mock_bindings):
        """Test start transitions to STARTED state."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            result = await runtime.start()

        assert runtime.runtime_state == LinuxRuntimeState.STARTED
        assert runtime.is_connected
        assert result["status"] == "started"
        mock_bindings.create.assert_called_once()
        mock_bindings.init.assert_called_once()
        mock_bindings.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_when_already_started(self, runtime, mock_bindings):
        """Test start returns early when already started."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            result = await runtime.start()

        assert result["status"] == "already_started"

    @pytest.mark.asyncio
    async def test_stop_transitions_to_stopped(self, runtime, mock_bindings):
        """Test stop transitions to STOPPED state."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            result = await runtime.stop()

        assert runtime.runtime_state == LinuxRuntimeState.STOPPED
        assert not runtime.is_connected
        assert result["status"] == "stopped"
        mock_bindings.stop.assert_called_once()
        mock_bindings.destroy.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self, runtime):
        """Test stop returns early when not started."""
        result = await runtime.stop()
        assert result["status"] == "not_started"

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_bindings):
        """Test async context manager."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            async with LinuxRuntime(library_path="/mock/libmara.so") as rt:
                assert rt.is_connected

            assert rt.runtime_state == LinuxRuntimeState.STOPPED

    @pytest.mark.asyncio
    async def test_context_manager_with_auto_arm(self, mock_bindings):
        """Test async context manager with auto_arm."""
        mock_bindings.get_state.return_value = MaraState.ARMED

        config = LinuxRuntimeConfig(auto_arm=True)
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            async with LinuxRuntime(config=config) as rt:
                mock_bindings.arm.assert_called_once()

    # =========================================================================
    # State Machine Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_arm(self, runtime, mock_bindings):
        """Test arm transitions state."""
        mock_bindings.get_state.return_value = MaraState.ARMED

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            result = await runtime.arm()

        assert runtime.robot_state == MaraState.ARMED
        assert runtime.is_armed
        mock_bindings.arm.assert_called_once()

    @pytest.mark.asyncio
    async def test_disarm(self, runtime, mock_bindings):
        """Test disarm transitions state."""
        mock_bindings.get_state.return_value = MaraState.IDLE

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.arm()
            result = await runtime.disarm()

        assert runtime.robot_state == MaraState.IDLE
        assert not runtime.is_armed
        mock_bindings.disarm.assert_called_once()

    @pytest.mark.asyncio
    async def test_estop(self, runtime, mock_bindings):
        """Test estop transitions to fault."""
        mock_bindings.get_state.return_value = MaraState.FAULT

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            result = await runtime.estop()

        assert runtime.robot_state == MaraState.FAULT
        mock_bindings.estop.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state(self, runtime, mock_bindings):
        """Test get_state returns current state."""
        mock_bindings.get_state.return_value = MaraState.ARMED

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            state = await runtime.get_state()

        assert state == MaraState.ARMED

    # =========================================================================
    # Servo Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_servo_attach(self, runtime, mock_bindings):
        """Test servo attach."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.servo_attach(0, 13, 500, 2500)

        mock_bindings.servo_attach.assert_called_once()

    @pytest.mark.asyncio
    async def test_servo_write_requires_armed(self, runtime, mock_bindings):
        """Test servo write requires armed state."""
        mock_bindings.get_state.return_value = MaraState.IDLE

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()

            with pytest.raises(RuntimeError, match="not armed"):
                await runtime.servo_write(0, 90.0)

    @pytest.mark.asyncio
    async def test_servo_write_when_armed(self, runtime, mock_bindings):
        """Test servo write when armed."""
        mock_bindings.get_state.return_value = MaraState.ARMED

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.arm()
            await runtime.servo_write(0, 90.0)

        mock_bindings.servo_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_servo_read(self, runtime, mock_bindings):
        """Test servo read."""
        mock_bindings.servo_read.return_value = 45.0

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            angle = await runtime.servo_read(0)

        assert angle == 45.0

    # =========================================================================
    # Motor Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_motor_set_requires_armed(self, runtime, mock_bindings):
        """Test motor set requires armed state."""
        mock_bindings.get_state.return_value = MaraState.IDLE

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()

            with pytest.raises(RuntimeError, match="not armed"):
                await runtime.motor_set(0, 50.0)

    @pytest.mark.asyncio
    async def test_motor_stop_all(self, runtime, mock_bindings):
        """Test motor stop all doesn't require armed."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.motor_stop_all()

        mock_bindings.motor_stop_all.assert_called_once()

    # =========================================================================
    # Motion Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_set_velocity_requires_armed(self, runtime, mock_bindings):
        """Test set_velocity requires armed state."""
        mock_bindings.get_state.return_value = MaraState.IDLE

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()

            with pytest.raises(RuntimeError, match="not armed"):
                await runtime.set_velocity(0.5, 0.1)

    @pytest.mark.asyncio
    async def test_stop_motion(self, runtime, mock_bindings):
        """Test stop motion doesn't require armed."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.stop_motion()

        mock_bindings.stop_motion.assert_called_once()

    # =========================================================================
    # Sensor Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_imu_read(self, runtime, mock_bindings):
        """Test IMU read returns ImuData."""
        mock_bindings.imu_read.return_value = (
            (0.1, 0.2, 1.0),  # accel
            (1.0, 2.0, 3.0),  # gyro
        )

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            imu = await runtime.imu_read()

        assert isinstance(imu, ImuData)
        assert imu.ax_g == 0.1
        assert imu.ay_g == 0.2
        assert imu.az_g == 1.0
        assert imu.gx_dps == 1.0
        assert imu.gy_dps == 2.0
        assert imu.gz_dps == 3.0

    @pytest.mark.asyncio
    async def test_encoder_read(self, runtime, mock_bindings):
        """Test encoder read."""
        mock_bindings.encoder_read.return_value = 5000

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            ticks = await runtime.encoder_read(0)

        assert ticks == 5000

    # =========================================================================
    # GPIO Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_gpio_mode(self, runtime, mock_bindings):
        """Test GPIO mode."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.gpio_mode(17, 1)  # Output

        mock_bindings.gpio_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpio_write(self, runtime, mock_bindings):
        """Test GPIO write."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            await runtime.gpio_write(17, True)

        mock_bindings.gpio_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpio_read(self, runtime, mock_bindings):
        """Test GPIO read."""
        mock_bindings.gpio_read.return_value = True

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            value = await runtime.gpio_read(17)

        assert value is True

    # =========================================================================
    # Diagnostics Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_identity(self, runtime, mock_bindings):
        """Test get identity returns dict."""
        mock_bindings.get_identity.return_value = '{"version": "1.0.0", "platform": "linux"}'

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            identity = await runtime.get_identity()

        assert identity["version"] == "1.0.0"
        assert identity["platform"] == "linux"

    @pytest.mark.asyncio
    async def test_get_health(self, runtime, mock_bindings):
        """Test get health returns dict."""
        mock_bindings.get_health.return_value = '{"healthy": true, "state": "IDLE"}'

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            health = await runtime.get_health()

        assert health["healthy"] is True
        assert health["state"] == "IDLE"

    def test_get_version(self, runtime, mock_bindings):
        """Test get version."""
        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            runtime._bindings = mock_bindings
            version = runtime.get_version()

        assert version == "1.0.0"

    # =========================================================================
    # Event Callback Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_state_change_callback(self, runtime, mock_bindings):
        """Test state change callback is called."""
        callback = MagicMock()
        mock_bindings.get_state.return_value = MaraState.ARMED

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            await runtime.start()
            runtime.on_state_change(callback)
            await runtime.arm()

        callback.assert_called_with(MaraState.ARMED)

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_operation_when_not_started_raises(self, runtime):
        """Test operations raise when not started."""
        with pytest.raises(RuntimeError, match="not started"):
            await runtime.arm()

    @pytest.mark.asyncio
    async def test_start_error_sets_error_state(self, mock_bindings):
        """Test start error sets ERROR state."""
        mock_bindings.init.side_effect = Exception("Init failed")

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            rt = LinuxRuntime()
            with pytest.raises(RuntimeError, match="Failed to start"):
                await rt.start()

            assert rt.runtime_state == LinuxRuntimeState.ERROR


class TestLinuxRuntimeIntegration:
    """Integration tests for LinuxRuntime with MaraRuntime."""

    @pytest.fixture
    def mock_bindings(self):
        """Create mock bindings."""
        bindings = MagicMock()
        bindings.create.return_value = MagicMock()
        bindings.init.return_value = None
        bindings.start.return_value = None
        bindings.stop.return_value = None
        bindings.destroy.return_value = None
        bindings.arm.return_value = None
        bindings.get_state.return_value = MaraState.IDLE
        bindings.version.return_value = "1.0.0"
        return bindings

    @pytest.mark.asyncio
    async def test_mara_runtime_linux_mode(self, mock_bindings):
        """Test MaraRuntime with linux_mode=True."""
        from mara_host.mcp.runtime import MaraRuntime

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            runtime = MaraRuntime(
                linux_mode=True,
                library_path="/mock/libmara.so",
            )

            result = await runtime.connect()

            assert result["status"] == "connected"
            assert result["mode"] == "linux"
            assert runtime.is_connected
            assert runtime.state.connected

            await runtime.disconnect()
            assert not runtime.is_connected

    @pytest.mark.asyncio
    async def test_mara_runtime_disconnect_in_linux_mode(self, mock_bindings):
        """Test MaraRuntime disconnect in linux_mode."""
        from mara_host.mcp.runtime import MaraRuntime

        with patch("mara_host.runtime.linux_runtime.MaraBindings", return_value=mock_bindings):
            runtime = MaraRuntime(linux_mode=True)

            await runtime.connect()
            result = await runtime.disconnect()

            assert result["status"] == "disconnected"
            assert runtime._linux_runtime is None
            assert not runtime.is_connected
