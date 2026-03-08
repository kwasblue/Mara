# mara_host/robot.py
"""
Robot - The main entry point for controlling a robot.

This provides a platform for connecting to and controlling robots built on
the ESP32 MCU Host firmware. HostModules are exposed as lazy properties for
direct hardware access.

Example:
    from mara_host import Robot

    async def main():
        async with Robot("/dev/ttyUSB0") as robot:
            await robot.arm()

            # GPIO control
            await robot.gpio.register(0, pin=2, mode="output")
            await robot.gpio.write(0, 1)
            await robot.gpio.toggle(0)

            # Motion control
            await robot.motion.set_velocity(0.3, 0.0)

    asyncio.run(main())

Optional features (opt-in):
    # Recording
    async with Robot("/dev/ttyUSB0") as robot:
        with robot.record("my_session"):
            await robot.arm()
            # ... events are recorded ...

    # Upload controller
    await robot.upload_controller(my_controller, slot=0)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Callable, Any, Dict, Union

if TYPE_CHECKING:
    from .command.client import MaraClient
    from .core.event_bus import EventBus
    from .api.gpio import GPIO
    from .services.control.motion_service import MotionService


class Session:
    """
    Recording session for capturing robot events.

    Use via robot.record() context manager.
    """

    def __init__(self, robot: "Robot", name: str, log_dir: str = "recordings"):
        self._robot = robot
        self._name = name
        self._log_dir = log_dir
        self._bundle = None
        self._original_bus = None
        self._recording_bus = None

    def start(self) -> None:
        """Start recording."""
        from .logger.logger import MaraLogBundle
        from .research.recording import RecordingEventBus

        os.makedirs(self._log_dir, exist_ok=True)

        self._bundle = MaraLogBundle(
            name=self._name,
            log_dir=self._log_dir,
            console=False,
        )

        # Wrap the event bus
        self._original_bus = self._robot._bus
        self._recording_bus = RecordingEventBus(self._original_bus, self._bundle)
        self._robot._bus = self._recording_bus

        # Also set on client if connected
        if self._robot._client:
            self._robot._client.bus = self._recording_bus

    def stop(self) -> str:
        """Stop recording and return path to recording file."""
        # Restore original bus
        if self._original_bus:
            self._robot._bus = self._original_bus
            if self._robot._client:
                self._robot._client.bus = self._original_bus

        path = ""
        if self._bundle:
            path = str(self._bundle.events.path) if hasattr(self._bundle.events, 'path') else ""
            self._bundle = None

        return path

    def __enter__(self) -> "Session":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class Robot:
    """
    Connection to a physical robot running ESP32 MCU Host firmware.

    This is the main entry point for the mara_host library. It handles:
    - Transport setup (serial or TCP)
    - Protocol handshake and version verification
    - Connection monitoring and heartbeat
    - Event routing via EventBus

    Args:
        port: Serial port path (e.g., "/dev/ttyUSB0", "COM3")
        host: TCP host for WiFi connection (e.g., "192.168.4.1")
        tcp_port: TCP port number (default: 3333)
        baudrate: Serial baud rate (default: 115200)

    Example - Serial connection:
        robot = Robot("/dev/ttyUSB0")
        await robot.connect()

    Example - TCP/WiFi connection:
        robot = Robot(host="192.168.4.1")
        await robot.connect()

    Example - Context manager (recommended):
        async with Robot("/dev/ttyUSB0") as robot:
            await robot.arm()
            # robot automatically disconnects on exit
    """

    def __init__(
        self,
        port: Optional[str] = None,
        host: Optional[str] = None,
        tcp_port: int = 3333,
        baudrate: int = 115200,
    ) -> None:
        if not port and not host:
            raise ValueError("Provide either port= (serial) or host= (TCP)")

        self._port = port
        self._host = host
        self._tcp_port = tcp_port
        self._baudrate = baudrate

        # Lazy-initialized on connect()
        self._transport = None
        self._bus: Optional[EventBus] = None
        self._client: Optional[MaraClient] = None
        self._connected = False

        # Lazy-initialized API / Services
        self._gpio: Optional[GPIO] = None
        self._motion: Optional[MotionService] = None

    def _setup(self) -> None:
        """Initialize transport, bus, and client (called by connect)."""
        from .core.event_bus import EventBus
        from .command.client import MaraClient

        # Create transport based on connection type
        if self._port:
            from .transport.serial_transport import SerialTransport
            self._transport = SerialTransport(self._port, self._baudrate)
        else:
            from .transport.tcp_transport import AsyncTcpTransport
            self._transport = AsyncTcpTransport(self._host, self._tcp_port)

        # Create event bus and client
        self._bus = EventBus()
        self._client = MaraClient(self._transport, self._bus)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Connect to the robot and perform handshake.

        This establishes the transport connection, verifies protocol version
        compatibility, and starts background tasks (heartbeat, monitoring).

        Raises:
            RuntimeError: If handshake fails or version mismatch
        """
        if self._connected:
            return

        if self._client is None:
            self._setup()

        await self._client.start()
        self._connected = True

    async def disconnect(self) -> None:
        """
        Disconnect from the robot.

        This stops all background tasks and closes the transport cleanly.
        """
        if not self._connected:
            return

        if self._client:
            await self._client.stop()

        self._connected = False

    async def __aenter__(self) -> "Robot":
        """Async context manager entry - connects to robot."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - disconnects from robot."""
        await self.disconnect()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def client(self) -> "MaraClient":
        """
        Access the underlying MaraClient.

        Use this for advanced operations not exposed by the Robot API.
        """
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._client

    @property
    def bus(self) -> "EventBus":
        """
        Access the EventBus for subscribing to events.

        Use robot.on() for a simpler subscription API.
        """
        if self._bus is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._bus

    @property
    def is_connected(self) -> bool:
        """Whether the robot is currently connected."""
        if self._client is None:
            return False
        return self._client.is_connected

    @property
    def capabilities(self) -> list[str]:
        """
        List of capabilities reported by the MCU.

        Returns feature names like ["WIFI", "IMU", "ENCODER", "STEPPER"].
        """
        if self._client is None:
            return []
        return self._client.features or []

    @property
    def firmware_version(self) -> Optional[str]:
        """Firmware version string from the MCU."""
        if self._client is None:
            return None
        return self._client.firmware_version

    @property
    def name(self) -> Optional[str]:
        """Platform name from MCU identity."""
        if self._client is None:
            return None
        return self._client.platform_name

    # -------------------------------------------------------------------------
    # Services (lazy-loaded)
    # -------------------------------------------------------------------------

    @property
    def gpio(self) -> "GPIO":
        """
        GPIO controller for digital I/O.

        Example:
            await robot.gpio.register(channel=0, pin=2, mode="output")
            await robot.gpio.write(channel=0, value=1)
            await robot.gpio.toggle(channel=0)
            await robot.gpio.high(0)
            await robot.gpio.low(0)
        """
        if self._gpio is None:
            from .api.gpio import GPIO
            self._gpio = GPIO(self)
        return self._gpio

    @property
    def motion(self) -> "MotionService":
        """
        Motion service for velocity control.

        Example:
            await robot.motion.set_velocity(vx=0.3, omega=0.0)
            await robot.motion.stop()
        """
        if self._motion is None:
            from .services.control.motion_service import MotionService
            self._motion = MotionService(self.client)
        return self._motion

    # -------------------------------------------------------------------------
    # Event Subscription
    # -------------------------------------------------------------------------

    def on(self, event: str, handler: Callable[[Any], None]) -> None:
        """
        Subscribe to robot events.

        Common events:
        - "telemetry" - All telemetry data
        - "telemetry.imu" - IMU data only
        - "telemetry.encoder0" - Encoder 0 data
        - "heartbeat" - Heartbeat received
        - "connection.lost" - Connection lost
        - "connection.restored" - Connection restored

        Args:
            event: Event topic name
            handler: Callback function receiving event data

        Example:
            def on_telemetry(data):
                print(f"IMU: {data.get('imu')}")

            robot.on("telemetry", on_telemetry)
        """
        if self._bus is None:
            self._setup()
        self._bus.subscribe(event, handler)

    # -------------------------------------------------------------------------
    # Safety & State Commands
    # -------------------------------------------------------------------------

    async def arm(self) -> tuple[bool, Optional[str]]:
        """
        Arm the robot (enable actuators).

        Returns:
            (success, error_message) tuple
        """
        return await self.client.arm()

    async def disarm(self) -> tuple[bool, Optional[str]]:
        """
        Disarm the robot (disable actuators).

        Returns:
            (success, error_message) tuple
        """
        return await self.client.disarm()

    async def activate(self) -> tuple[bool, Optional[str]]:
        """
        Activate the robot (start control loops).

        Returns:
            (success, error_message) tuple
        """
        return await self.client.activate()

    async def deactivate(self) -> tuple[bool, Optional[str]]:
        """
        Deactivate the robot (stop control loops).

        Returns:
            (success, error_message) tuple
        """
        return await self.client.deactivate()

    async def estop(self) -> tuple[bool, Optional[str]]:
        """
        Emergency stop - immediately halt all actuators.

        Returns:
            (success, error_message) tuple
        """
        return await self.client.estop()

    async def clear_estop(self) -> tuple[bool, Optional[str]]:
        """
        Clear emergency stop state.

        Returns:
            (success, error_message) tuple
        """
        return await self.client.clear_estop()

    async def stop(self) -> tuple[bool, Optional[str]]:
        """
        Stop all motion (but don't trigger E-STOP).

        Returns:
            (success, error_message) tuple
        """
        return await self.client.cmd_stop()

    # -------------------------------------------------------------------------
    # Telemetry Control
    # -------------------------------------------------------------------------

    async def set_telemetry_interval(self, interval_ms: int) -> None:
        """
        Set telemetry reporting interval.

        Args:
            interval_ms: Interval in milliseconds (e.g., 100 for 10Hz)
        """
        await self.client.cmd_telem_set_interval(interval_ms=interval_ms)

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    async def set_velocity(self, vx: float, omega: float) -> tuple[bool, Optional[str]]:
        """
        Set robot velocity (for differential drive robots).

        Args:
            vx: Linear velocity in m/s
            omega: Angular velocity in rad/s

        Returns:
            (success, error_message) tuple
        """
        return await self.client.set_vel(vx, omega)

    @classmethod
    def from_config(
        cls,
        config_path: Union[str, Path],
        profile: Optional[str] = None,
    ) -> "Robot":
        """
        Create a Robot from a YAML configuration file.

        Args:
            config_path: Path to YAML configuration file
            profile: Optional profile name (e.g., "bench", "field", "sim")

        Returns:
            Robot instance (not yet connected)

        Example:
            async with Robot.from_config("robots/my_robot.yaml") as robot:
                await robot.arm()
                await robot.gpio.write(0, 1)

            # With profile override
            async with Robot.from_config("robots/my_robot.yaml", profile="bench") as robot:
                ...
        """
        from .config import RobotConfig

        config = RobotConfig.load(config_path, profile=profile)
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid config: {'; '.join(errors)}")
        return config.create_robot()

    def __repr__(self) -> str:
        conn_type = "serial" if self._port else "tcp"
        addr = self._port or f"{self._host}:{self._tcp_port}"
        status = "connected" if self._connected else "disconnected"
        return f"Robot({conn_type}={addr!r}, {status})"


def load_config(config_path: Union[str, Path]) -> "RobotConfig":
    """
    Load a robot configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        RobotConfig instance

    Example:
        config = load_config("robots/my_robot.yaml")
        errors = config.validate()
        robot = config.create_robot()
    """
    from .config import RobotConfig
    return RobotConfig.load(config_path)


def robot_from_config(config: Union[Dict[str, Any], "RobotConfig"]) -> Robot:
    """
    Create a Robot instance from a configuration.

    Args:
        config: RobotConfig or raw dict

    Returns:
        Robot instance (not yet connected)

    Example:
        config = load_config("robots/my_robot.yaml")
        robot = robot_from_config(config)
        await robot.connect()
    """
    from .config import RobotConfig

    if isinstance(config, dict):
        config = RobotConfig.from_dict(config)

    return config.create_robot()


# Keep old dict-based function for backward compatibility
def _robot_from_dict(config: Dict[str, Any]) -> Robot:
    """Internal: create Robot from raw dict (backward compat)."""
    transport = config.get("transport", {})
    transport_type = transport.get("type", "serial")

    if transport_type == "serial":
        return Robot(
            port=transport.get("port", "/dev/ttyUSB0"),
            baudrate=transport.get("baudrate", 115200),
        )
    elif transport_type == "tcp":
        return Robot(
            host=transport.get("host", "192.168.4.1"),
            tcp_port=transport.get("port", 3333),
        )
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")
