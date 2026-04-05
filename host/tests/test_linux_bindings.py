"""Tests for Linux bindings (mara_bindings.py)."""

import pytest
from unittest.mock import MagicMock, patch, create_autospec
from ctypes import c_void_p, c_int, c_float, c_uint8, c_int32

from mara_host.bindings.mara_bindings import (
    MaraBindings,
    MaraError,
    MaraState,
    MaraBindingsError,
)


class TestMaraError:
    """Tests for MaraError enum."""

    def test_error_values(self):
        """Test error code values match C API."""
        assert MaraError.OK == 0
        assert MaraError.INVALID_ARG == 1
        assert MaraError.INVALID_STATE == 2
        assert MaraError.NOT_INITIALIZED == 3
        assert MaraError.NOT_ARMED == 4
        assert MaraError.HARDWARE == 5
        assert MaraError.TIMEOUT == 6
        assert MaraError.BUFFER_TOO_SMALL == 7
        assert MaraError.NOT_SUPPORTED == 8
        assert MaraError.INTERNAL == 9


class TestMaraState:
    """Tests for MaraState enum."""

    def test_state_values(self):
        """Test state values match C API."""
        assert MaraState.IDLE == 0
        assert MaraState.ARMED == 1
        assert MaraState.ACTIVE == 2
        assert MaraState.FAULT == 3
        assert MaraState.UNKNOWN == 4


class TestMaraBindingsError:
    """Tests for MaraBindingsError exception."""

    def test_exception_with_error_code(self):
        """Test exception stores error code."""
        err = MaraBindingsError(MaraError.NOT_ARMED, "Robot not armed")
        assert err.error_code == MaraError.NOT_ARMED
        assert "Robot not armed" in str(err)

    def test_exception_default_message(self):
        """Test exception with default message."""
        err = MaraBindingsError(MaraError.TIMEOUT)
        assert "TIMEOUT" in str(err)


class TestMaraBindings:
    """Tests for MaraBindings ctypes wrapper."""

    @pytest.fixture
    def mock_lib(self):
        """Create a mock ctypes library."""
        lib = MagicMock()

        # Setup return values for functions
        lib.mara_create.return_value = 0  # MARA_OK
        lib.mara_init.return_value = 0
        lib.mara_start.return_value = 0
        lib.mara_stop.return_value = 0
        lib.mara_destroy.return_value = 0

        lib.mara_arm.return_value = 0
        lib.mara_disarm.return_value = 0
        lib.mara_activate.return_value = 0
        lib.mara_deactivate.return_value = 0
        lib.mara_estop.return_value = 0
        lib.mara_clear_estop.return_value = 0
        lib.mara_get_state.return_value = 0
        lib.mara_get_state_string.return_value = 0

        lib.mara_gpio_mode.return_value = 0
        lib.mara_gpio_write.return_value = 0
        lib.mara_gpio_read.return_value = 0

        lib.mara_servo_attach.return_value = 0
        lib.mara_servo_detach.return_value = 0
        lib.mara_servo_write.return_value = 0
        lib.mara_servo_read.return_value = 0

        lib.mara_motor_set.return_value = 0
        lib.mara_motor_stop.return_value = 0
        lib.mara_motor_stop_all.return_value = 0

        lib.mara_set_velocity.return_value = 0
        lib.mara_motion_forward.return_value = 0
        lib.mara_motion_backward.return_value = 0
        lib.mara_motion_rotate_left.return_value = 0
        lib.mara_motion_rotate_right.return_value = 0
        lib.mara_stop_motion.return_value = 0

        lib.mara_imu_read.return_value = 0
        lib.mara_encoder_read.return_value = 0
        lib.mara_ultrasonic_read.return_value = 0

        lib.mara_execute_json.return_value = 0
        lib.mara_get_identity.return_value = 0
        lib.mara_get_health.return_value = 0

        lib.mara_error_string.return_value = b"Success"
        lib.mara_state_string.return_value = b"IDLE"
        lib.mara_version.return_value = b"1.0.0"

        return lib

    @pytest.fixture
    def bindings(self, mock_lib):
        """Create bindings with mocked library."""
        with patch("ctypes.CDLL", return_value=mock_lib):
            bindings = MaraBindings("libmara_capi.so")
            bindings._lib = mock_lib
            return bindings

    # =========================================================================
    # Lifecycle Tests
    # =========================================================================

    def test_create_returns_handle(self, bindings, mock_lib):
        """Test create returns a handle."""
        handle = bindings.create()
        mock_lib.mara_create.assert_called_once()

    def test_init_calls_library(self, bindings, mock_lib):
        """Test init calls the library."""
        handle = c_void_p(1234)
        bindings.init(handle, '{"test": true}')
        mock_lib.mara_init.assert_called_once()

    def test_start_calls_library(self, bindings, mock_lib):
        """Test start calls the library."""
        handle = c_void_p(1234)
        bindings.start(handle)
        mock_lib.mara_start.assert_called_once()

    def test_stop_calls_library(self, bindings, mock_lib):
        """Test stop calls the library."""
        handle = c_void_p(1234)
        bindings.stop(handle)
        mock_lib.mara_stop.assert_called_once()

    def test_destroy_calls_library(self, bindings, mock_lib):
        """Test destroy calls the library."""
        handle = c_void_p(1234)
        bindings.destroy(handle)
        mock_lib.mara_destroy.assert_called_once()

    # =========================================================================
    # State Machine Tests
    # =========================================================================

    def test_arm_calls_library(self, bindings, mock_lib):
        """Test arm calls the library."""
        handle = c_void_p(1234)
        bindings.arm(handle)
        mock_lib.mara_arm.assert_called_once()

    def test_disarm_calls_library(self, bindings, mock_lib):
        """Test disarm calls the library."""
        handle = c_void_p(1234)
        bindings.disarm(handle)
        mock_lib.mara_disarm.assert_called_once()

    def test_estop_calls_library(self, bindings, mock_lib):
        """Test estop calls the library."""
        handle = c_void_p(1234)
        bindings.estop(handle)
        mock_lib.mara_estop.assert_called_once()

    def test_get_state_returns_enum(self, bindings, mock_lib):
        """Test get_state returns MaraState enum."""
        handle = c_void_p(1234)

        # Mock the state pointer modification
        def set_state(handle, state_ptr):
            state_ptr._obj.value = MaraState.ARMED
            return 0

        mock_lib.mara_get_state.side_effect = set_state
        state = bindings.get_state(handle)
        assert isinstance(state, MaraState)

    # =========================================================================
    # GPIO Tests
    # =========================================================================

    def test_gpio_mode_calls_library(self, bindings, mock_lib):
        """Test gpio_mode calls the library."""
        handle = c_void_p(1234)
        bindings.gpio_mode(handle, 17, 1)  # Pin 17, Output mode
        mock_lib.mara_gpio_mode.assert_called_once()

    def test_gpio_write_calls_library(self, bindings, mock_lib):
        """Test gpio_write calls the library."""
        handle = c_void_p(1234)
        bindings.gpio_write(handle, 17, True)
        mock_lib.mara_gpio_write.assert_called_once()

    def test_gpio_read_calls_library(self, bindings, mock_lib):
        """Test gpio_read calls the library."""
        handle = c_void_p(1234)
        bindings.gpio_read(handle, 17)
        mock_lib.mara_gpio_read.assert_called_once()

    # =========================================================================
    # Servo Tests
    # =========================================================================

    def test_servo_attach_calls_library(self, bindings, mock_lib):
        """Test servo_attach calls the library."""
        handle = c_void_p(1234)
        bindings.servo_attach(handle, 0, 13, 500, 2500)
        mock_lib.mara_servo_attach.assert_called_once()

    def test_servo_write_calls_library(self, bindings, mock_lib):
        """Test servo_write calls the library."""
        handle = c_void_p(1234)
        bindings.servo_write(handle, 0, 90.0)
        mock_lib.mara_servo_write.assert_called_once()

    # =========================================================================
    # Motion Tests
    # =========================================================================

    def test_set_velocity_calls_library(self, bindings, mock_lib):
        """Test set_velocity calls the library."""
        handle = c_void_p(1234)
        bindings.set_velocity(handle, 0.5, 0.1)
        mock_lib.mara_set_velocity.assert_called_once()

    def test_motion_forward_calls_library(self, bindings, mock_lib):
        """Test motion_forward calls the library."""
        handle = c_void_p(1234)
        bindings.motion_forward(handle, 50.0)
        mock_lib.mara_motion_forward.assert_called_once()

    def test_stop_motion_calls_library(self, bindings, mock_lib):
        """Test stop_motion calls the library."""
        handle = c_void_p(1234)
        bindings.stop_motion(handle)
        mock_lib.mara_stop_motion.assert_called_once()

    # =========================================================================
    # Sensor Tests
    # =========================================================================

    def test_imu_read_returns_tuple(self, bindings, mock_lib):
        """Test imu_read returns acceleration and gyro tuples."""
        handle = c_void_p(1234)

        def set_imu_values(handle, ax, ay, az, gx, gy, gz):
            ax._obj.value = 0.1
            ay._obj.value = 0.2
            az._obj.value = 1.0
            gx._obj.value = 0.01
            gy._obj.value = 0.02
            gz._obj.value = 0.03
            return 0

        mock_lib.mara_imu_read.side_effect = set_imu_values
        accel, gyro = bindings.imu_read(handle)

        assert len(accel) == 3
        assert len(gyro) == 3

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_error_raises_exception(self, bindings, mock_lib):
        """Test errors raise MaraBindingsError."""
        mock_lib.mara_arm.return_value = MaraError.NOT_INITIALIZED
        handle = c_void_p(1234)

        with pytest.raises(MaraBindingsError) as exc_info:
            bindings.arm(handle)

        assert exc_info.value.error_code == MaraError.NOT_INITIALIZED

    def test_version_returns_string(self, bindings, mock_lib):
        """Test version returns string."""
        version = bindings.version()
        assert version == "1.0.0"

    # =========================================================================
    # Library Loading Tests
    # =========================================================================

    def test_library_not_found_raises_error(self):
        """Test library not found raises MaraBindingsError."""
        with patch("ctypes.CDLL", side_effect=OSError("Library not found")):
            with pytest.raises(MaraBindingsError) as exc_info:
                MaraBindings("/nonexistent/path/libmara_capi.so")

            assert exc_info.value.error_code == MaraError.INTERNAL
