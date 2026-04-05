"""
Linux Runtime - In-process MARA runtime for Linux robots

Provides an alternative to the serial/TCP transport when running
directly on a Linux robot (Raspberry Pi, Jetson, etc.)

Instead of communicating with an ESP32 over serial, this runtime
loads libmara_capi.so and runs the MARA firmware directly in-process.

This enables:
- Lower latency (no serial/network overhead)
- Direct hardware access (GPIO, I2C, PWM)
- Single-binary deployment on Linux SBCs

Usage:
    from mara_host.runtime.linux_runtime import LinuxRuntime

    async def main():
        rt = LinuxRuntime(library_path="/usr/local/lib/libmara_capi.so")
        await rt.start()
        await rt.arm()

        # Control the robot
        await rt.servo_write(0, 90.0)
        imu = await rt.imu_read()

        await rt.stop()

    asyncio.run(main())

Or using the context manager:
    async with LinuxRuntime() as rt:
        await rt.arm()
        await rt.servo_write(0, 90.0)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List
from enum import Enum

from ..bindings import MaraBindings, MaraError, MaraState


class LinuxRuntimeState(str, Enum):
    """Runtime lifecycle states"""
    CREATED = "created"
    INITIALIZING = "initializing"
    STARTED = "started"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class LinuxRuntimeConfig:
    """Configuration for LinuxRuntime"""
    library_path: Optional[str] = None
    gpio_chip: str = "/dev/gpiochip0"
    i2c_bus: int = 1
    pwm_chip: int = 0
    log_level: str = "info"
    auto_arm: bool = False


@dataclass
class ImuData:
    """IMU sensor data"""
    ax_g: float = 0.0
    ay_g: float = 0.0
    az_g: float = 0.0
    gx_dps: float = 0.0
    gy_dps: float = 0.0
    gz_dps: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class LinuxRuntime:
    """
    In-process MARA runtime for Linux robots

    Provides the same interface as MaraRuntime but runs the firmware
    directly via libmara_capi.so instead of communicating over serial.

    Thread Safety:
    - All public methods are async and use an internal lock
    - Safe to call from multiple coroutines

    State Machine:
    - IDLE -> ARMED -> ACTIVE (same as ESP32 firmware)
    - Must call arm() before actuator commands
    """

    def __init__(
        self,
        library_path: Optional[str] = None,
        config: Optional[LinuxRuntimeConfig] = None,
        **kwargs
    ):
        """
        Initialize LinuxRuntime

        Args:
            library_path: Path to libmara_capi.so (optional)
            config: Runtime configuration (optional)
            **kwargs: Config overrides (gpio_chip, i2c_bus, etc.)
        """
        self._config = config or LinuxRuntimeConfig()
        if library_path:
            self._config.library_path = library_path

        # Apply kwargs overrides
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        self._bindings: Optional[MaraBindings] = None
        self._handle = None
        self._state = LinuxRuntimeState.CREATED
        self._robot_state = MaraState.UNKNOWN
        self._lock = asyncio.Lock()

        # Event callbacks
        self._state_callbacks: List[Callable[[MaraState], None]] = []
        self._telemetry_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    @property
    def is_connected(self) -> bool:
        """Check if runtime is started"""
        return self._state == LinuxRuntimeState.STARTED

    @property
    def is_armed(self) -> bool:
        """Check if robot is armed"""
        return self._robot_state in (MaraState.ARMED, MaraState.ACTIVE)

    @property
    def robot_state(self) -> MaraState:
        """Get current robot state"""
        return self._robot_state

    @property
    def runtime_state(self) -> LinuxRuntimeState:
        """Get runtime lifecycle state"""
        return self._state

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def __aenter__(self) -> "LinuxRuntime":
        """Async context manager entry"""
        await self.start()
        if self._config.auto_arm:
            await self.arm()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> Dict[str, Any]:
        """
        Start the runtime

        Loads the shared library, initializes the HAL, and starts
        the firmware core.

        Returns:
            Dict with runtime info (version, state)
        """
        async with self._lock:
            if self._state == LinuxRuntimeState.STARTED:
                return {"status": "already_started"}

            self._state = LinuxRuntimeState.INITIALIZING

            try:
                # Load bindings
                self._bindings = MaraBindings(self._config.library_path)

                # Create runtime
                self._handle = self._bindings.create()

                # Build config JSON
                config_json = json.dumps({
                    "gpio_chip": self._config.gpio_chip,
                    "i2c_bus": self._config.i2c_bus,
                    "pwm_chip": self._config.pwm_chip,
                    "log_level": self._config.log_level,
                })

                # Initialize
                self._bindings.init(self._handle, config_json)

                # Start
                self._bindings.start(self._handle)

                self._state = LinuxRuntimeState.STARTED
                self._robot_state = self._bindings.get_state(self._handle)

                return {
                    "status": "started",
                    "version": self._bindings.version(),
                    "state": self._robot_state.name,
                }

            except Exception as e:
                self._state = LinuxRuntimeState.ERROR
                raise RuntimeError(f"Failed to start runtime: {e}") from e

    async def stop(self) -> Dict[str, Any]:
        """
        Stop the runtime

        Stops all hardware, disarms the robot, and unloads the library.

        Returns:
            Dict with stop status
        """
        async with self._lock:
            if self._state != LinuxRuntimeState.STARTED:
                return {"status": "not_started"}

            self._state = LinuxRuntimeState.STOPPING

            try:
                # Stop runtime
                self._bindings.stop(self._handle)

                # Destroy runtime
                self._bindings.destroy(self._handle)

                self._handle = None
                self._bindings = None
                self._state = LinuxRuntimeState.STOPPED
                self._robot_state = MaraState.UNKNOWN

                return {"status": "stopped"}

            except Exception as e:
                self._state = LinuxRuntimeState.ERROR
                raise RuntimeError(f"Failed to stop runtime: {e}") from e

    # =========================================================================
    # State Machine
    # =========================================================================

    async def arm(self) -> Dict[str, Any]:
        """Arm the robot"""
        self._ensure_started()
        self._bindings.arm(self._handle)
        self._robot_state = self._bindings.get_state(self._handle)
        self._notify_state_change()
        return {"state": self._robot_state.name}

    async def disarm(self) -> Dict[str, Any]:
        """Disarm the robot"""
        self._ensure_started()
        self._bindings.disarm(self._handle)
        self._robot_state = self._bindings.get_state(self._handle)
        self._notify_state_change()
        return {"state": self._robot_state.name}

    async def activate(self) -> Dict[str, Any]:
        """Activate the robot"""
        self._ensure_started()
        self._bindings.activate(self._handle)
        self._robot_state = self._bindings.get_state(self._handle)
        self._notify_state_change()
        return {"state": self._robot_state.name}

    async def deactivate(self) -> Dict[str, Any]:
        """Deactivate the robot"""
        self._ensure_started()
        self._bindings.deactivate(self._handle)
        self._robot_state = self._bindings.get_state(self._handle)
        self._notify_state_change()
        return {"state": self._robot_state.name}

    async def estop(self) -> Dict[str, Any]:
        """Emergency stop"""
        self._ensure_started()
        self._bindings.estop(self._handle)
        self._robot_state = self._bindings.get_state(self._handle)
        self._notify_state_change()
        return {"state": self._robot_state.name}

    async def clear_estop(self) -> Dict[str, Any]:
        """Clear emergency stop"""
        self._ensure_started()
        self._bindings.clear_estop(self._handle)
        self._robot_state = self._bindings.get_state(self._handle)
        self._notify_state_change()
        return {"state": self._robot_state.name}

    async def get_state(self) -> MaraState:
        """Get current robot state"""
        self._ensure_started()
        self._robot_state = self._bindings.get_state(self._handle)
        return self._robot_state

    # =========================================================================
    # GPIO
    # =========================================================================

    async def gpio_mode(self, pin: int, mode: int):
        """Set GPIO pin mode (0=Input, 1=Output, 2=PullUp, 3=PullDown)"""
        self._ensure_started()
        self._bindings.gpio_mode(self._handle, pin, mode)

    async def gpio_write(self, pin: int, value: bool):
        """Write digital value to GPIO pin"""
        self._ensure_started()
        self._bindings.gpio_write(self._handle, pin, value)

    async def gpio_read(self, pin: int) -> bool:
        """Read digital value from GPIO pin"""
        self._ensure_started()
        return self._bindings.gpio_read(self._handle, pin)

    # =========================================================================
    # Servo
    # =========================================================================

    async def servo_attach(self, servo_id: int, pin: int,
                           min_us: int = 500, max_us: int = 2500):
        """Attach a servo to a pin"""
        self._ensure_started()
        self._bindings.servo_attach(self._handle, servo_id, pin, min_us, max_us)

    async def servo_detach(self, servo_id: int):
        """Detach a servo"""
        self._ensure_started()
        self._bindings.servo_detach(self._handle, servo_id)

    async def servo_write(self, servo_id: int, angle: float):
        """Write angle to servo (0-180 degrees)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.servo_write(self._handle, servo_id, angle)

    async def servo_read(self, servo_id: int) -> float:
        """Read current servo angle"""
        self._ensure_started()
        return self._bindings.servo_read(self._handle, servo_id)

    # =========================================================================
    # Motor
    # =========================================================================

    async def motor_set(self, motor_id: int, speed: float):
        """Set motor speed (-100 to 100 percent)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.motor_set(self._handle, motor_id, speed)

    async def motor_stop(self, motor_id: int):
        """Stop a motor"""
        self._ensure_started()
        self._bindings.motor_stop(self._handle, motor_id)

    async def motor_stop_all(self):
        """Stop all motors"""
        self._ensure_started()
        self._bindings.motor_stop_all(self._handle)

    # =========================================================================
    # Motion
    # =========================================================================

    async def set_velocity(self, vx: float, omega: float):
        """Set robot velocity (m/s linear, rad/s angular)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.set_velocity(self._handle, vx, omega)

    async def motion_forward(self, speed: float):
        """Move forward at speed (0-100)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.motion_forward(self._handle, speed)

    async def motion_backward(self, speed: float):
        """Move backward at speed (0-100)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.motion_backward(self._handle, speed)

    async def motion_rotate_left(self, speed: float):
        """Rotate left at speed (0-100)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.motion_rotate_left(self._handle, speed)

    async def motion_rotate_right(self, speed: float):
        """Rotate right at speed (0-100)"""
        self._ensure_started()
        self._ensure_armed()
        self._bindings.motion_rotate_right(self._handle, speed)

    async def stop_motion(self):
        """Stop all motion"""
        self._ensure_started()
        self._bindings.stop_motion(self._handle)

    # =========================================================================
    # Sensors
    # =========================================================================

    async def imu_read(self) -> ImuData:
        """Read IMU data"""
        self._ensure_started()
        accel, gyro = self._bindings.imu_read(self._handle)

        return ImuData(
            ax_g=accel[0],
            ay_g=accel[1],
            az_g=accel[2],
            gx_dps=gyro[0],
            gy_dps=gyro[1],
            gz_dps=gyro[2],
            timestamp=datetime.now(),
        )

    async def encoder_read(self, encoder_id: int) -> int:
        """Read encoder ticks"""
        self._ensure_started()
        return self._bindings.encoder_read(self._handle, encoder_id)

    async def ultrasonic_read(self, sensor_id: int) -> float:
        """Read ultrasonic distance in cm"""
        self._ensure_started()
        return self._bindings.ultrasonic_read(self._handle, sensor_id)

    # =========================================================================
    # Diagnostics
    # =========================================================================

    async def get_identity(self) -> Dict[str, Any]:
        """Get runtime identity as dict"""
        self._ensure_started()
        json_str = self._bindings.get_identity(self._handle)
        return json.loads(json_str)

    async def get_health(self) -> Dict[str, Any]:
        """Get runtime health as dict"""
        self._ensure_started()
        json_str = self._bindings.get_health(self._handle)
        return json.loads(json_str)

    def get_version(self) -> str:
        """Get library version"""
        if self._bindings:
            return self._bindings.version()
        return "unknown"

    # =========================================================================
    # Events
    # =========================================================================

    def on_state_change(self, callback: Callable[[MaraState], None]):
        """Register callback for state changes"""
        self._state_callbacks.append(callback)

    def on_telemetry(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for telemetry updates"""
        self._telemetry_callbacks.append(callback)

    # =========================================================================
    # Private
    # =========================================================================

    def _ensure_started(self):
        """Raise if runtime not started"""
        if self._state != LinuxRuntimeState.STARTED:
            raise RuntimeError("Runtime not started. Call start() first.")

    def _ensure_armed(self):
        """Raise if robot not armed"""
        if not self.is_armed:
            raise RuntimeError(
                f"Robot not armed. Current state: {self._robot_state.name}. "
                "Call arm() first."
            )

    def _notify_state_change(self):
        """Notify state change callbacks"""
        for callback in self._state_callbacks:
            try:
                callback(self._robot_state)
            except Exception:
                pass  # Don't let callback errors crash runtime
