"""
MARA Bindings - ctypes wrapper for libmara_capi.so

Provides low-level Python bindings to the MARA runtime C API.
This module handles the ctypes FFI layer, translating between
Python and C types.

Usage:
    from mara_host.bindings import MaraBindings

    bindings = MaraBindings("/usr/local/lib/libmara_capi.so")
    rt = bindings.create()
    bindings.init(rt, "{}")
    bindings.start(rt)
    bindings.arm(rt)

    # Use the robot...
    bindings.servo_write(rt, 0, 90.0)

    bindings.stop(rt)
    bindings.destroy(rt)
"""

from __future__ import annotations

import ctypes
from ctypes import (
    POINTER, c_void_p, c_int, c_uint8, c_int32, c_uint16, c_uint32,
    c_float, c_char_p, c_size_t, byref, create_string_buffer
)
from enum import IntEnum
from pathlib import Path
from typing import Optional, Tuple


class MaraError(IntEnum):
    """MARA error codes (matches mara_error_t)"""
    OK = 0
    INVALID_ARG = 1
    INVALID_STATE = 2
    NOT_INITIALIZED = 3
    NOT_ARMED = 4
    HARDWARE = 5
    TIMEOUT = 6
    BUFFER_TOO_SMALL = 7
    NOT_SUPPORTED = 8
    INTERNAL = 9


class MaraState(IntEnum):
    """MARA robot states (matches mara_state_t)"""
    IDLE = 0
    ARMED = 1
    ACTIVE = 2
    FAULT = 3
    UNKNOWN = 4


class MaraBindingsError(Exception):
    """Exception raised by MaraBindings operations"""

    def __init__(self, error_code: MaraError, message: str = ""):
        self.error_code = error_code
        self.message = message or f"MARA error: {error_code.name}"
        super().__init__(self.message)


class MaraBindings:
    """
    ctypes wrapper for libmara_capi.so

    Provides a Python-friendly interface to the MARA C API.
    All methods that can fail raise MaraBindingsError on error.
    """

    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize bindings with path to libmara_capi.so

        Args:
            library_path: Path to the shared library.
                         If None, searches standard paths.
        """
        self._lib = self._load_library(library_path)
        self._setup_functions()

    def _load_library(self, path: Optional[str]) -> ctypes.CDLL:
        """Load the shared library"""
        search_paths = []

        if path:
            search_paths.append(path)
        else:
            # Standard search paths
            search_paths = [
                "libmara_capi.so",
                "/usr/local/lib/libmara_capi.so",
                "/usr/lib/libmara_capi.so",
                str(Path.home() / ".local/lib/libmara_capi.so"),
            ]

        for lib_path in search_paths:
            try:
                return ctypes.CDLL(lib_path)
            except OSError:
                continue

        raise MaraBindingsError(
            MaraError.INTERNAL,
            f"Could not load libmara_capi.so from: {search_paths}"
        )

    def _setup_functions(self):
        """Configure ctypes function signatures"""
        lib = self._lib

        # === Lifecycle ===
        lib.mara_create.argtypes = [POINTER(c_void_p)]
        lib.mara_create.restype = c_int

        lib.mara_init.argtypes = [c_void_p, c_char_p]
        lib.mara_init.restype = c_int

        lib.mara_start.argtypes = [c_void_p]
        lib.mara_start.restype = c_int

        lib.mara_stop.argtypes = [c_void_p]
        lib.mara_stop.restype = c_int

        lib.mara_destroy.argtypes = [c_void_p]
        lib.mara_destroy.restype = c_int

        # === State Machine ===
        lib.mara_arm.argtypes = [c_void_p]
        lib.mara_arm.restype = c_int

        lib.mara_disarm.argtypes = [c_void_p]
        lib.mara_disarm.restype = c_int

        lib.mara_activate.argtypes = [c_void_p]
        lib.mara_activate.restype = c_int

        lib.mara_deactivate.argtypes = [c_void_p]
        lib.mara_deactivate.restype = c_int

        lib.mara_estop.argtypes = [c_void_p]
        lib.mara_estop.restype = c_int

        lib.mara_clear_estop.argtypes = [c_void_p]
        lib.mara_clear_estop.restype = c_int

        lib.mara_get_state.argtypes = [c_void_p, POINTER(c_int)]
        lib.mara_get_state.restype = c_int

        lib.mara_get_state_string.argtypes = [c_void_p, c_char_p, c_size_t]
        lib.mara_get_state_string.restype = c_int

        # === GPIO ===
        lib.mara_gpio_mode.argtypes = [c_void_p, c_uint8, c_uint8]
        lib.mara_gpio_mode.restype = c_int

        lib.mara_gpio_write.argtypes = [c_void_p, c_uint8, c_uint8]
        lib.mara_gpio_write.restype = c_int

        lib.mara_gpio_read.argtypes = [c_void_p, c_uint8, POINTER(c_uint8)]
        lib.mara_gpio_read.restype = c_int

        # === Servo ===
        lib.mara_servo_attach.argtypes = [c_void_p, c_uint8, c_uint8, c_uint16, c_uint16]
        lib.mara_servo_attach.restype = c_int

        lib.mara_servo_detach.argtypes = [c_void_p, c_uint8]
        lib.mara_servo_detach.restype = c_int

        lib.mara_servo_write.argtypes = [c_void_p, c_uint8, c_float]
        lib.mara_servo_write.restype = c_int

        lib.mara_servo_read.argtypes = [c_void_p, c_uint8, POINTER(c_float)]
        lib.mara_servo_read.restype = c_int

        # === Motor ===
        lib.mara_motor_set.argtypes = [c_void_p, c_uint8, c_float]
        lib.mara_motor_set.restype = c_int

        lib.mara_motor_stop.argtypes = [c_void_p, c_uint8]
        lib.mara_motor_stop.restype = c_int

        lib.mara_motor_stop_all.argtypes = [c_void_p]
        lib.mara_motor_stop_all.restype = c_int

        # === Motion ===
        lib.mara_set_velocity.argtypes = [c_void_p, c_float, c_float]
        lib.mara_set_velocity.restype = c_int

        lib.mara_motion_forward.argtypes = [c_void_p, c_float]
        lib.mara_motion_forward.restype = c_int

        lib.mara_motion_backward.argtypes = [c_void_p, c_float]
        lib.mara_motion_backward.restype = c_int

        lib.mara_motion_rotate_left.argtypes = [c_void_p, c_float]
        lib.mara_motion_rotate_left.restype = c_int

        lib.mara_motion_rotate_right.argtypes = [c_void_p, c_float]
        lib.mara_motion_rotate_right.restype = c_int

        lib.mara_stop_motion.argtypes = [c_void_p]
        lib.mara_stop_motion.restype = c_int

        # === Sensors ===
        lib.mara_imu_read.argtypes = [
            c_void_p,
            POINTER(c_float), POINTER(c_float), POINTER(c_float),
            POINTER(c_float), POINTER(c_float), POINTER(c_float)
        ]
        lib.mara_imu_read.restype = c_int

        lib.mara_encoder_read.argtypes = [c_void_p, c_uint8, POINTER(c_int32)]
        lib.mara_encoder_read.restype = c_int

        lib.mara_ultrasonic_read.argtypes = [c_void_p, c_uint8, POINTER(c_float)]
        lib.mara_ultrasonic_read.restype = c_int

        # === JSON ===
        lib.mara_execute_json.argtypes = [
            c_void_p, c_char_p, c_char_p, c_size_t, POINTER(c_size_t)
        ]
        lib.mara_execute_json.restype = c_int

        # === Diagnostics ===
        lib.mara_get_identity.argtypes = [c_void_p, c_char_p, c_size_t]
        lib.mara_get_identity.restype = c_int

        lib.mara_get_health.argtypes = [c_void_p, c_char_p, c_size_t]
        lib.mara_get_health.restype = c_int

        # === Utilities ===
        lib.mara_error_string.argtypes = [c_int]
        lib.mara_error_string.restype = c_char_p

        lib.mara_state_string.argtypes = [c_int]
        lib.mara_state_string.restype = c_char_p

        lib.mara_version.argtypes = []
        lib.mara_version.restype = c_char_p

    def _check(self, result: int, operation: str = "operation"):
        """Check result code and raise exception on error"""
        if result != MaraError.OK:
            error = MaraError(result)
            error_str = self._lib.mara_error_string(result)
            msg = error_str.decode() if error_str else error.name
            raise MaraBindingsError(error, f"{operation} failed: {msg}")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def create(self) -> c_void_p:
        """Create a new runtime instance"""
        handle = c_void_p()
        self._check(self._lib.mara_create(byref(handle)), "create")
        return handle

    def init(self, handle: c_void_p, config_json: str = "{}"):
        """Initialize the runtime with configuration"""
        self._check(
            self._lib.mara_init(handle, config_json.encode()),
            "init"
        )

    def start(self, handle: c_void_p):
        """Start the runtime"""
        self._check(self._lib.mara_start(handle), "start")

    def stop(self, handle: c_void_p):
        """Stop the runtime"""
        self._check(self._lib.mara_stop(handle), "stop")

    def destroy(self, handle: c_void_p):
        """Destroy the runtime"""
        self._check(self._lib.mara_destroy(handle), "destroy")

    # =========================================================================
    # State Machine
    # =========================================================================

    def arm(self, handle: c_void_p):
        """Arm the robot"""
        self._check(self._lib.mara_arm(handle), "arm")

    def disarm(self, handle: c_void_p):
        """Disarm the robot"""
        self._check(self._lib.mara_disarm(handle), "disarm")

    def activate(self, handle: c_void_p):
        """Activate the robot"""
        self._check(self._lib.mara_activate(handle), "activate")

    def deactivate(self, handle: c_void_p):
        """Deactivate the robot"""
        self._check(self._lib.mara_deactivate(handle), "deactivate")

    def estop(self, handle: c_void_p):
        """Emergency stop"""
        self._check(self._lib.mara_estop(handle), "estop")

    def clear_estop(self, handle: c_void_p):
        """Clear emergency stop"""
        self._check(self._lib.mara_clear_estop(handle), "clear_estop")

    def get_state(self, handle: c_void_p) -> MaraState:
        """Get current robot state"""
        state = c_int()
        self._check(self._lib.mara_get_state(handle, byref(state)), "get_state")
        return MaraState(state.value)

    def get_state_string(self, handle: c_void_p) -> str:
        """Get current state as string"""
        buf = create_string_buffer(32)
        self._check(
            self._lib.mara_get_state_string(handle, buf, len(buf)),
            "get_state_string"
        )
        return buf.value.decode()

    # =========================================================================
    # GPIO
    # =========================================================================

    def gpio_mode(self, handle: c_void_p, pin: int, mode: int):
        """Set GPIO pin mode (0=Input, 1=Output, 2=PullUp, 3=PullDown)"""
        self._check(
            self._lib.mara_gpio_mode(handle, pin, mode),
            "gpio_mode"
        )

    def gpio_write(self, handle: c_void_p, pin: int, value: bool):
        """Write digital value to GPIO pin"""
        self._check(
            self._lib.mara_gpio_write(handle, pin, 1 if value else 0),
            "gpio_write"
        )

    def gpio_read(self, handle: c_void_p, pin: int) -> bool:
        """Read digital value from GPIO pin"""
        value = c_uint8()
        self._check(
            self._lib.mara_gpio_read(handle, pin, byref(value)),
            "gpio_read"
        )
        return bool(value.value)

    # =========================================================================
    # Servo
    # =========================================================================

    def servo_attach(self, handle: c_void_p, servo_id: int, pin: int,
                     min_us: int = 500, max_us: int = 2500):
        """Attach a servo to a pin"""
        self._check(
            self._lib.mara_servo_attach(handle, servo_id, pin, min_us, max_us),
            "servo_attach"
        )

    def servo_detach(self, handle: c_void_p, servo_id: int):
        """Detach a servo"""
        self._check(
            self._lib.mara_servo_detach(handle, servo_id),
            "servo_detach"
        )

    def servo_write(self, handle: c_void_p, servo_id: int, angle: float):
        """Write angle to servo (0-180 degrees)"""
        self._check(
            self._lib.mara_servo_write(handle, servo_id, angle),
            "servo_write"
        )

    def servo_read(self, handle: c_void_p, servo_id: int) -> float:
        """Read current servo angle"""
        angle = c_float()
        self._check(
            self._lib.mara_servo_read(handle, servo_id, byref(angle)),
            "servo_read"
        )
        return angle.value

    # =========================================================================
    # Motor
    # =========================================================================

    def motor_set(self, handle: c_void_p, motor_id: int, speed: float):
        """Set motor speed (-100 to 100 percent)"""
        self._check(
            self._lib.mara_motor_set(handle, motor_id, speed),
            "motor_set"
        )

    def motor_stop(self, handle: c_void_p, motor_id: int):
        """Stop a motor"""
        self._check(
            self._lib.mara_motor_stop(handle, motor_id),
            "motor_stop"
        )

    def motor_stop_all(self, handle: c_void_p):
        """Stop all motors"""
        self._check(
            self._lib.mara_motor_stop_all(handle),
            "motor_stop_all"
        )

    # =========================================================================
    # Motion
    # =========================================================================

    def set_velocity(self, handle: c_void_p, vx: float, omega: float):
        """Set robot velocity (m/s linear, rad/s angular)"""
        self._check(
            self._lib.mara_set_velocity(handle, vx, omega),
            "set_velocity"
        )

    def motion_forward(self, handle: c_void_p, speed: float):
        """Move forward at speed (0-100)"""
        self._check(
            self._lib.mara_motion_forward(handle, speed),
            "motion_forward"
        )

    def motion_backward(self, handle: c_void_p, speed: float):
        """Move backward at speed (0-100)"""
        self._check(
            self._lib.mara_motion_backward(handle, speed),
            "motion_backward"
        )

    def motion_rotate_left(self, handle: c_void_p, speed: float):
        """Rotate left at speed (0-100)"""
        self._check(
            self._lib.mara_motion_rotate_left(handle, speed),
            "motion_rotate_left"
        )

    def motion_rotate_right(self, handle: c_void_p, speed: float):
        """Rotate right at speed (0-100)"""
        self._check(
            self._lib.mara_motion_rotate_right(handle, speed),
            "motion_rotate_right"
        )

    def stop_motion(self, handle: c_void_p):
        """Stop all motion"""
        self._check(
            self._lib.mara_stop_motion(handle),
            "stop_motion"
        )

    # =========================================================================
    # Sensors
    # =========================================================================

    def imu_read(self, handle: c_void_p) -> Tuple[
        Tuple[float, float, float],  # accel (ax, ay, az)
        Tuple[float, float, float]   # gyro (gx, gy, gz)
    ]:
        """
        Read IMU data

        Returns:
            Tuple of (accel, gyro) where each is (x, y, z)
            Accel in g, gyro in deg/s
        """
        ax, ay, az = c_float(), c_float(), c_float()
        gx, gy, gz = c_float(), c_float(), c_float()

        self._check(
            self._lib.mara_imu_read(
                handle,
                byref(ax), byref(ay), byref(az),
                byref(gx), byref(gy), byref(gz)
            ),
            "imu_read"
        )

        return (
            (ax.value, ay.value, az.value),
            (gx.value, gy.value, gz.value)
        )

    def encoder_read(self, handle: c_void_p, encoder_id: int) -> int:
        """Read encoder ticks"""
        ticks = c_int32()
        self._check(
            self._lib.mara_encoder_read(handle, encoder_id, byref(ticks)),
            "encoder_read"
        )
        return ticks.value

    def ultrasonic_read(self, handle: c_void_p, sensor_id: int) -> float:
        """Read ultrasonic distance in cm"""
        distance = c_float()
        self._check(
            self._lib.mara_ultrasonic_read(handle, sensor_id, byref(distance)),
            "ultrasonic_read"
        )
        return distance.value

    # =========================================================================
    # JSON
    # =========================================================================

    def execute_json(self, handle: c_void_p, command: str) -> str:
        """Execute a JSON command and return response"""
        response_buf = create_string_buffer(4096)
        actual = c_size_t()

        self._check(
            self._lib.mara_execute_json(
                handle,
                command.encode(),
                response_buf,
                len(response_buf),
                byref(actual)
            ),
            "execute_json"
        )

        return response_buf.value.decode()

    # =========================================================================
    # Diagnostics
    # =========================================================================

    def get_identity(self, handle: c_void_p) -> str:
        """Get runtime identity as JSON"""
        buf = create_string_buffer(512)
        self._check(
            self._lib.mara_get_identity(handle, buf, len(buf)),
            "get_identity"
        )
        return buf.value.decode()

    def get_health(self, handle: c_void_p) -> str:
        """Get runtime health as JSON"""
        buf = create_string_buffer(512)
        self._check(
            self._lib.mara_get_health(handle, buf, len(buf)),
            "get_health"
        )
        return buf.value.decode()

    # =========================================================================
    # Utilities
    # =========================================================================

    def error_string(self, error_code: int) -> str:
        """Get error string for error code"""
        result = self._lib.mara_error_string(error_code)
        return result.decode() if result else "Unknown error"

    def state_string(self, state: int) -> str:
        """Get state string for state enum"""
        result = self._lib.mara_state_string(state)
        return result.decode() if result else "UNKNOWN"

    def version(self) -> str:
        """Get library version"""
        result = self._lib.mara_version()
        return result.decode() if result else "unknown"
