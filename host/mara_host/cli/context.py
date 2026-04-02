# mara_host/cli/context.py
"""
CLI context manager for service-based command execution.

Provides a unified context that handles connection lifecycle and
exposes services for CLI commands.
"""

from __future__ import annotations

import asyncio
import functools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, TypeVar, ParamSpec

from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient
    from mara_host.services.control.motor_service import MotorService
    from mara_host.services.control.servo_service import ServoService
    from mara_host.services.control.gpio_service import GpioService
    from mara_host.services.control.stepper_service import StepperService
    from mara_host.services.control.encoder_service import EncoderService
    from mara_host.services.control.i2c_service import I2cService
    from mara_host.services.control.imu_service import ImuService
    from mara_host.services.control.ultrasonic_service import UltrasonicService
    from mara_host.services.control.pwm_service import PwmService
    from mara_host.services.control.wifi_service import WifiService
    from mara_host.services.control.control_graph_service import ControlGraphService
    from mara_host.services.control.controller_service import ControllerService
    from mara_host.services.control.pid_service import PidService
    from mara_host.services.control.state_service import StateService
    from mara_host.services.transport.connection_service import ConnectionService


P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class CLIContextConfig:
    """Configuration for CLI context."""

    port: Optional[str] = None  # Uses cli_config default if not set
    baudrate: int = DEFAULT_BAUDRATE
    host: Optional[str] = None  # For TCP connections
    tcp_port: int = 3333
    ble_name: Optional[str] = None  # For Bluetooth SPP connections


class CLIContext:
    """
    Context manager for CLI commands with service access.

    Handles connection lifecycle and provides lazy-loaded services
    for robot control operations.

    Example:
        async with CLIContext(port="/dev/ttyUSB0") as ctx:
            result = await ctx.motor_service.set_speed(0, 0.5)
            if result.ok:
                print("Motor speed set!")
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: Optional[int] = None,
        host: Optional[str] = None,
        tcp_port: Optional[int] = None,
        ble_name: Optional[str] = None,
        verbose: bool = True,
        robot_config: Optional[object] = None,
        robot_config_path: Optional[str] = None,
    ):
        """
        Initialize CLI context.

        Args:
            port: Serial port for connection (uses config default if None)
            baudrate: Serial baudrate (uses config default if None)
            host: TCP host (if using TCP instead of serial)
            tcp_port: TCP port number (uses config default if None)
            ble_name: Bluetooth SPP device name (if using BLE instead of serial/TCP)
            verbose: If False, suppress client status messages
        """
        from mara_host.cli.cli_config import (
            get_serial_port,
            get_baudrate,
            get_tcp_port,
            get_robot_config_path,
        )

        self.port = port or get_serial_port()
        self.baudrate = baudrate or get_baudrate()
        self.host = host
        self.tcp_port = tcp_port or get_tcp_port()
        self.ble_name = ble_name
        self.verbose = verbose
        self.robot_config = robot_config
        self.robot_config_path = robot_config_path or get_robot_config_path()

        self._connection: Optional["ConnectionService"] = None
        self._client: Optional["MaraClient"] = None
        self._telemetry = None  # TelemetryService instance

        # Cached services (lazy-loaded)
        self._state_service: Optional["StateService"] = None
        self._motor_service: Optional["MotorService"] = None
        self._servo_service: Optional["ServoService"] = None
        self._gpio_service: Optional["GpioService"] = None
        self._stepper_service: Optional["StepperService"] = None
        self._encoder_service: Optional["EncoderService"] = None
        self._i2c_service: Optional["I2cService"] = None
        self._imu_service: Optional["ImuService"] = None
        self._ultrasonic_service: Optional["UltrasonicService"] = None
        self._pwm_service: Optional["PwmService"] = None
        self._wifi_service: Optional["WifiService"] = None
        self._control_graph_service: Optional["ControlGraphService"] = None
        self._controller_service: Optional["ControllerService"] = None
        self._pid_service: Optional["PidService"] = None
        self._mcu_diagnostics_service = None
        self._motion_service = None
        self._signal_service = None
        self._camera_control_service = None
        self._policy_robot = None

    @classmethod
    def from_args(cls, args) -> "CLIContext":
        """
        Create CLIContext from argparse namespace.

        Args:
            args: Parsed arguments with port, host, tcp_port, quiet attributes

        Returns:
            Configured CLIContext
        """
        # quiet flag inverts verbose
        verbose = not getattr(args, "quiet", False)
        return cls(
            port=getattr(args, "port", None),
            baudrate=getattr(args, "baudrate", None),
            host=getattr(args, "tcp", None) or getattr(args, "host", None),
            tcp_port=getattr(args, "tcp_port", None),
            ble_name=getattr(args, "ble_name", None),
            verbose=verbose,
            robot_config_path=getattr(args, "robot_config", None),
        )

    async def connect(self) -> None:
        """Establish connection to the robot."""
        from mara_host.services.transport import (
            ConnectionService,
            ConnectionConfig,
            TransportType,
        )
        from mara_host.services.telemetry import TelemetryService

        if self.host:
            # TCP connection
            config = ConnectionConfig(
                transport_type=TransportType.TCP,
                host=self.host,
                tcp_port=self.tcp_port,
                verbose=self.verbose,
            )
        elif self.ble_name:
            # Bluetooth SPP connection
            config = ConnectionConfig(
                transport_type=TransportType.BLE,
                ble_name=self.ble_name,
                baudrate=self.baudrate,
                verbose=self.verbose,
            )
        else:
            # Serial connection
            config = ConnectionConfig(
                transport_type=TransportType.SERIAL,
                port=self.port,
                baudrate=self.baudrate,
                verbose=self.verbose,
            )

        self._connection = ConnectionService(config)
        await self._connection.connect()
        self._client = self._connection.client

        # Start telemetry (required for arm/actuator commands)
        self._telemetry = TelemetryService(self._client)
        await self._telemetry.start(interval_ms=100)
        await asyncio.sleep(0.1)  # Wait for telemetry to stabilize

        # Auto-arm for CLI commands (use state_service for convergence)
        result = await self.state_service.arm()
        await asyncio.sleep(0.1)  # Allow state to settle before actuator commands

    async def disconnect(self) -> None:
        """Disconnect from the robot."""
        # Disarm before disconnecting (use state_service for convergence)
        if self._state_service:
            try:
                await self._state_service.disarm()
            except Exception:
                pass  # Ignore errors on disarm

        # Stop telemetry
        if self._telemetry:
            self._telemetry.stop()
            self._telemetry = None

        if self._mcu_diagnostics_service is not None:
            self._mcu_diagnostics_service.close()
            self._mcu_diagnostics_service = None

        if self._connection:
            await self._connection.disconnect()
            self._connection = None
            self._client = None

        # Clear cached services
        self._state_service = None
        self._motor_service = None
        self._servo_service = None
        self._gpio_service = None
        self._stepper_service = None
        self._encoder_service = None
        self._i2c_service = None
        self._imu_service = None
        self._ultrasonic_service = None
        self._pwm_service = None
        self._wifi_service = None
        self._control_graph_service = None
        self._controller_service = None
        self._pid_service = None
        self._mcu_diagnostics_service = None
        self._motion_service = None
        self._signal_service = None
        self._camera_control_service = None
        self._policy_robot = None
        self._generated_services = None

    async def __aenter__(self) -> "CLIContext":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    def _resolve_robot_config(self):
        if self.robot_config is not None:
            return self.robot_config
        if not self.robot_config_path:
            return None
        from mara_host.config import RobotConfig
        self.robot_config = RobotConfig.load(self.robot_config_path)
        return self.robot_config

    def _sensor_policy_provider(self):
        config = self._resolve_robot_config()
        if config is None:
            return None
        if self._policy_robot is None:
            robot = config.create_robot()
            robot._client = self._client
            robot._bus = getattr(self._client, "bus", None)
            robot._connected = self.is_connected
            self._policy_robot = robot
        else:
            self._policy_robot._client = self._client
            self._policy_robot._bus = getattr(self._client, "bus", None)
            self._policy_robot._connected = self.is_connected
        return self._policy_robot.sensors

    def _control_graph_persistence_store(self):
        config = self._resolve_robot_config()
        persistence = getattr(config, "persistence", None)
        if persistence is None:
            return None
        policy = persistence.control_graph
        if not policy.enabled or policy.backend == "none":
            return None
        from mara_host.services.persistence.store import ControlGraphStore
        return ControlGraphStore(persistence.root_dir)

    def _diagnostic_persistence_store(self):
        config = self._resolve_robot_config()
        persistence = getattr(config, "persistence", None)
        if persistence is None:
            return None
        policy = persistence.diagnostics
        if not policy.enabled or policy.backend == "none":
            return None
        from mara_host.services.persistence.store import DiagnosticRecordStore
        return DiagnosticRecordStore(persistence.root_dir)

    @property
    def client(self) -> "MaraClient":
        """Get the underlying MaraClient."""
        if self._client is None:
            raise RuntimeError("Not connected. Use 'async with CLIContext()' or call connect() first.")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self._client is not None

    # ==================== Service Properties ====================

    @property
    def state_service(self) -> "StateService":
        """Get or create StateService instance."""
        if self._state_service is None:
            from mara_host.services.control.state_service import StateService
            self._state_service = StateService(self.client)
        return self._state_service

    @property
    def motor_service(self) -> "MotorService":
        """Get or create MotorService instance."""
        if self._motor_service is None:
            from mara_host.services.control.motor_service import MotorService
            self._motor_service = MotorService(self.client)
        return self._motor_service

    @property
    def servo_service(self) -> "ServoService":
        """Get or create ServoService instance."""
        if self._servo_service is None:
            from mara_host.services.control.servo_service import ServoService
            self._servo_service = ServoService(self.client)
        return self._servo_service

    @property
    def gpio_service(self) -> "GpioService":
        """Get or create GpioService instance."""
        if self._gpio_service is None:
            from mara_host.services.control.gpio_service import GpioService
            self._gpio_service = GpioService(self.client)
        return self._gpio_service

    @property
    def stepper_service(self) -> "StepperService":
        """Get or create StepperService instance."""
        if self._stepper_service is None:
            from mara_host.services.control.stepper_service import StepperService
            self._stepper_service = StepperService(self.client)
        return self._stepper_service

    @property
    def encoder_service(self) -> "EncoderService":
        """Get or create EncoderService instance."""
        if self._encoder_service is None:
            from mara_host.services.control.encoder_service import EncoderService
            self._encoder_service = EncoderService(self.client)
        return self._encoder_service

    @property
    def i2c_service(self) -> "I2cService":
        """Get or create I2cService instance."""
        if self._i2c_service is None:
            from mara_host.services.control.i2c_service import I2cService
            self._i2c_service = I2cService(self.client)
        return self._i2c_service

    @property
    def imu_service(self) -> "ImuService":
        """Get or create ImuService instance."""
        if self._imu_service is None:
            from mara_host.services.control.imu_service import ImuService
            self._imu_service = ImuService(self.client)
        return self._imu_service

    @property
    def ultrasonic_service(self) -> "UltrasonicService":
        """Get or create UltrasonicService instance."""
        if self._ultrasonic_service is None:
            from mara_host.services.control.ultrasonic_service import UltrasonicService
            self._ultrasonic_service = UltrasonicService(self.client)
        return self._ultrasonic_service

    @property
    def pwm_service(self) -> "PwmService":
        """Get or create PwmService instance."""
        if self._pwm_service is None:
            from mara_host.services.control.pwm_service import PwmService
            self._pwm_service = PwmService(self.client)
        return self._pwm_service

    @property
    def wifi_service(self) -> "WifiService":
        """Get or create WifiService instance."""
        if self._wifi_service is None:
            from mara_host.services.control.wifi_service import WifiService
            self._wifi_service = WifiService(self.client)
        return self._wifi_service

    @property
    def control_graph_service(self) -> "ControlGraphService":
        """Get or create ControlGraphService instance."""
        if self._control_graph_service is None:
            from mara_host.services.control.control_graph_service import ControlGraphService
            self._control_graph_service = ControlGraphService(
                self.client,
                sensor_policy_provider=self._sensor_policy_provider,
                persistence_store=self._control_graph_persistence_store(),
            )
        return self._control_graph_service

    @property
    def controller_service(self) -> "ControllerService":
        """Get or create ControllerService instance."""
        if self._controller_service is None:
            from mara_host.services.control.controller_service import ControllerService
            self._controller_service = ControllerService(self.client)
        return self._controller_service

    @property
    def mcu_diagnostics_service(self):
        """Get or create the MCU diagnostics persistence service."""
        if self._mcu_diagnostics_service is None:
            from mara_host.services.persistence import McuDiagnosticsService
            self._mcu_diagnostics_service = McuDiagnosticsService(
                self.client,
                diagnostics_store=self._diagnostic_persistence_store(),
            )
        return self._mcu_diagnostics_service

    @property
    def pid_service(self) -> "PidService":
        """Get or create PidService instance."""
        if self._pid_service is None:
            from mara_host.services.control.pid_service import PidService
            self._pid_service = PidService(self.client)
        return self._pid_service

    @property
    def motion_service(self):
        """Get or create MotionService instance."""
        if self._motion_service is None:
            from mara_host.services.control.motion_service import MotionService
            self._motion_service = MotionService(self.client)
        return self._motion_service

    @property
    def signal_service(self):
        """Get or create SignalService instance."""
        if self._signal_service is None:
            from mara_host.services.control.signal_service import SignalService
            self._signal_service = SignalService(self.client)
        return self._signal_service

    @property
    def camera_control_service(self):
        """Get or create CameraControlService instance."""
        if self._camera_control_service is None:
            from mara_host.services.camera.camera_control_service import CameraControlService
            self._camera_control_service = CameraControlService(self.client)
        return self._camera_control_service

    # Generated services cache
    _generated_services: dict = None

    def get_generated_service(self, category: str):
        """
        Get a generated service by category.

        Generated services provide thin wrappers around firmware commands.
        Use these when there's no manual service with richer functionality,
        or for command categories not covered by manual services.

        Args:
            category: Service category (e.g., "servo", "dc", "stepper", "bench")

        Returns:
            Generated service instance, or None if category not found
        """
        if self._client is None:
            return None

        # Lazy init cache
        if self._generated_services is None:
            self._generated_services = {}

        if category not in self._generated_services:
            from mara_host.services._generated_services import get_generated_service
            self._generated_services[category] = get_generated_service(self.client, category)

        return self._generated_services.get(category)

    def list_generated_service_categories(self) -> list[str]:
        """List all available generated service categories."""
        from mara_host.services._generated_services import list_categories
        return list_categories()


def run_with_context(func: Callable[..., T]) -> Callable[..., int]:
    """
    Decorator that wraps an async CLI command function with context management.

    The decorated function receives the parsed args and a connected CLIContext.
    Connection errors are handled and reported appropriately.

    Example:
        @run_with_context
        async def cmd_motor_set(args, ctx: CLIContext) -> int:
            result = await ctx.motor_service.set_speed(args.id, args.speed)
            if result.ok:
                print_success(f"Motor {args.id}: speed set to {args.speed}")
                return 0
            else:
                print_error(result.error)
                return 1
    """
    @functools.wraps(func)
    def wrapper(args) -> int:
        from mara_host.cli.console import print_error

        async def run():
            ctx = CLIContext.from_args(args)
            try:
                async with ctx:
                    return await func(args, ctx)
            except ConnectionError as e:
                print_error(f"Connection failed: {e}")
                return 1
            except Exception as e:
                print_error(f"Error: {e}")
                return 1

        return asyncio.run(run())

    return wrapper


def run_with_context_no_connect(func: Callable[..., T]) -> Callable[..., int]:
    """
    Decorator that creates a CLIContext but doesn't auto-connect.

    Useful for commands that need manual connection control
    (e.g., for long-running operations with reconnection).

    Example:
        @run_with_context_no_connect
        async def cmd_monitor(args, ctx: CLIContext) -> int:
            await ctx.connect()
            try:
                # Long-running operation...
            finally:
                await ctx.disconnect()
    """
    @functools.wraps(func)
    def wrapper(args) -> int:
        from mara_host.cli.console import print_error

        async def run():
            ctx = CLIContext.from_args(args)
            try:
                return await func(args, ctx)
            except Exception as e:
                print_error(f"Error: {e}")
                return 1

        return asyncio.run(run())

    return wrapper
