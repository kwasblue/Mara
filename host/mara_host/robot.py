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

from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE

if TYPE_CHECKING:
    from .command.client import MaraClient
    from .core.event_bus import EventBus
    from .api.gpio import GPIO
    from .services.control.motion_service import MotionService
    from .services.control.motor_service import MotorService
    from .services.control.servo_service import ServoService
    from .api.sensors import SensorsFacade


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
    - Transport setup (serial, Bluetooth SPP, or TCP)
    - Protocol handshake and version verification
    - Connection monitoring and heartbeat
    - Event routing via EventBus

    Args:
        port: Serial port path (e.g., "/dev/ttyUSB0", "COM3")
        host: TCP host for WiFi connection (e.g., "192.168.4.1")
        ble_name: Bluetooth Classic SPP device name (e.g., "ESP32-SPP")
        tcp_port: TCP port number (default: 3333)
        baudrate: Serial/BLE baud rate hint (default: 115200)

    Example - Serial connection:
        robot = Robot("/dev/ttyUSB0")
        await robot.connect()

    Example - TCP/WiFi connection:
        robot = Robot(host="192.168.4.1")
        await robot.connect()

    Example - Bluetooth Classic SPP connection:
        robot = Robot(ble_name="ESP32-SPP")
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
        ble_name: Optional[str] = None,
        tcp_port: int = 3333,
        baudrate: int = DEFAULT_BAUDRATE,
        signing_key: Optional[bytes] = None,
    ) -> None:
        selected = sum(bool(v) for v in (port, host, ble_name))
        if selected != 1:
            raise ValueError("Provide exactly one of port= (serial), host= (TCP), or ble_name= (Bluetooth SPP)")

        self._port = port
        self._host = host
        self._ble_name = ble_name
        self._tcp_port = tcp_port
        self._baudrate = baudrate
        self._signing_key = signing_key

        # Lazy-initialized on connect()
        self._transport = None
        self._bus: Optional[EventBus] = None
        self._client: Optional[MaraClient] = None
        self._connected = False

        # Lazy-initialized API / Services
        self._gpio: Optional[GPIO] = None
        self._motion: Optional[MotionService] = None
        self._motor_service: Optional[MotorService] = None
        self._servo_service: Optional[ServoService] = None
        self._sensors = None
        self._config = None
        self._control_graph_service = None
        self._mcu_diagnostics_service = None

    def _setup(self) -> None:
        """Initialize transport, bus, and client (called by connect)."""
        from .core.event_bus import EventBus
        from .command.client import MaraClient

        # Create transport based on connection type
        if self._port:
            from .transport.serial_transport import SerialTransport
            self._transport = SerialTransport(self._port, self._baudrate)
        elif self._ble_name:
            from .transport.bluetooth_transport import BluetoothSerialTransport
            self._transport = BluetoothSerialTransport.auto(
                device_name=self._ble_name,
                baudrate=self._baudrate,
            )
        else:
            from .transport.tcp_transport import AsyncTcpTransport
            self._transport = AsyncTcpTransport(self._host, self._tcp_port)

        # Create event bus and client
        self._bus = EventBus()
        handshake_timeout_s = 4.0 if (self._port or self._ble_name) else 5.0
        self._client = MaraClient(
            self._transport,
            self._bus,
            handshake_timeout_s=handshake_timeout_s,
            signing_key=self._signing_key,
        )

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

    async def disconnect(self, validate_cleanup: bool = False) -> None:
        """
        Disconnect from the robot.

        This stops all background tasks and closes the transport cleanly.

        Args:
            validate_cleanup: If True, warn about leaked event subscriptions
        """
        if not self._connected:
            return

        # Close services with explicit cleanup methods
        # This unsubscribes any event handlers they registered
        for service in [
            self._control_graph_service,
            self._mcu_diagnostics_service,
            self._motion,
            self._motor_service,
            self._servo_service,
        ]:
            if service is not None and hasattr(service, 'close'):
                try:
                    service.close()
                except Exception:
                    pass  # Best-effort cleanup

        # Clear all lazy-loaded service references
        # (they hold stale client references after disconnect)
        self._gpio = None
        self._motion = None
        self._motor_service = None
        self._servo_service = None
        self._sensors = None
        self._control_graph_service = None
        self._mcu_diagnostics_service = None

        # Stop client (transport, monitors, heartbeat)
        if self._client:
            await self._client.stop()

        # Validate cleanup if requested
        if validate_cleanup and self._bus is not None:
            remaining = self._bus.get_subscription_count()
            if remaining:
                import warnings
                warnings.warn(f"Subscription leak: {remaining}", ResourceWarning)

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
    def config(self):
        """Optional RobotConfig attached when created from config helpers."""
        return self._config

    def get_sensor_config(self, name: str):
        """Return a configured sensor entry if this robot came from RobotConfig."""
        if self._config is None:
            return None
        return self._config.get_sensor(name)

    def _sensor_policy_provider(self):
        if self._config is None:
            return None
        return self.sensors

    def _control_graph_persistence_store(self):
        persistence = getattr(self._config, "persistence", None)
        if persistence is None:
            return None
        policy = persistence.control_graph
        if not policy.enabled or policy.backend == "none":
            return None
        from .services.persistence.store import ControlGraphStore
        return ControlGraphStore(persistence.root_dir)

    def _diagnostic_persistence_store(self):
        persistence = getattr(self._config, "persistence", None)
        if persistence is None:
            return None
        policy = persistence.diagnostics
        if not policy.enabled or policy.backend == "none":
            return None
        from .services.persistence.store import DiagnosticRecordStore
        return DiagnosticRecordStore(persistence.root_dir)

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

    @property
    def motor_service(self) -> "MotorService":
        """
        Shared motor service instance.

        Used internally by DCMotor API. Access directly for low-level control.
        """
        if self._motor_service is None:
            from .services.control.motor_service import MotorService
            self._motor_service = MotorService(self.client)
        return self._motor_service

    @property
    def servo_service(self) -> "ServoService":
        """
        Shared servo service instance.

        Used internally by Servo API. Access directly for low-level control.
        """
        if self._servo_service is None:
            from .services.control.servo_service import ServoService
            self._servo_service = ServoService(self.client)
        return self._servo_service

    @property
    def sensors(self) -> "SensorsFacade":
        """Thin config-aware sensor facade layered on existing APIs/services."""
        if self._sensors is None:
            from .api.sensors import SensorsFacade
            self._sensors = SensorsFacade(self)
        return self._sensors

    @property
    def control_graph_service(self):
        """Config-aware control-graph service bound to this robot when available."""
        if self._control_graph_service is None:
            from .services.control.control_graph_service import ControlGraphService
            self._control_graph_service = ControlGraphService(
                self.client,
                sensor_policy_provider=self._sensor_policy_provider,
                persistence_store=self._control_graph_persistence_store(),
            )
        return self._control_graph_service

    @property
    def mcu_diagnostics_service(self):
        """Service for reading persisted MCU diagnostics from telemetry."""
        if self._mcu_diagnostics_service is None:
            from .services.persistence import McuDiagnosticsService
            self._mcu_diagnostics_service = McuDiagnosticsService(
                self.client,
                diagnostics_store=self._diagnostic_persistence_store(),
            )
        return self._mcu_diagnostics_service

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

    def off(self, event: str, handler: Callable[[Any], None]) -> None:
        """
        Unsubscribe from robot events.

        Args:
            event: Event topic name
            handler: Callback function to remove
        """
        if self._bus is None:
            return
        self._bus.unsubscribe(event, handler)

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
        report = config.validate_report()
        if report.errors:
            raise ValueError(f"Invalid config: {'; '.join(report.errors)}")
        return config.create_robot()

    def __repr__(self) -> str:
        if self._port:
            conn_type = "serial"
            addr = self._port
        elif self._ble_name:
            conn_type = "ble"
            addr = self._ble_name
        else:
            conn_type = "tcp"
            addr = f"{self._host}:{self._tcp_port}"
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
