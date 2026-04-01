# mara_host/services/transport/connection_service.py
"""
Connection management service.

Provides a clean interface for creating and managing robot connections
across different transports.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Any
import logging

from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE


class TransportType(Enum):
    """Supported transport types."""
    SERIAL = "serial"
    BLE = "ble"
    TCP = "tcp"
    CAN = "can"
    MQTT = "mqtt"


@dataclass
class ConnectionConfig:
    """Configuration for a robot connection."""
    transport_type: TransportType

    # Serial options
    port: str = "/dev/ttyUSB0"
    baudrate: int = DEFAULT_BAUDRATE

    # TCP options
    host: str = "192.168.4.1"
    tcp_port: int = 3333

    # BLE options
    ble_name: str = "ESP32-SPP"

    # CAN options
    can_channel: str = "can0"
    can_bustype: str = "socketcan"
    can_node_id: int = 0

    # Client options
    connection_timeout_s: float = 6.0
    handshake_timeout_s: float = 4.0
    heartbeat_interval_s: float = 0.2
    require_version_match: bool = True

    # Logging options
    log_level: int = logging.INFO
    log_dir: str = "logs"
    verbose: bool = True


@dataclass
class ConnectionInfo:
    """Information about an active connection."""
    transport_type: TransportType
    firmware_version: Optional[str] = None
    protocol_version: Optional[int] = None
    board: Optional[str] = None
    platform_name: Optional[str] = None
    features: list = None
    capabilities: int = 0

    def __post_init__(self):
        if self.features is None:
            self.features = []


class ConnectionService:
    """
    Service for managing robot connections.

    Example:
        config = ConnectionConfig(
            transport_type=TransportType.SERIAL,
            port="/dev/ttyUSB0"
        )

        async with ConnectionService(config) as service:
            await service.client.cmd_arm()
            # ... use the robot
    """

    def __init__(self, config: ConnectionConfig):
        """
        Initialize connection service.

        Args:
            config: Connection configuration
        """
        self.config = config
        self.client = None
        self.transport = None

    async def connect(self) -> ConnectionInfo:
        """
        Establish connection to the robot.

        Returns:
            ConnectionInfo with robot details
        """
        from mara_host.command.client import MaraClient

        # Create transport based on type
        self.transport = self._create_transport()

        # Create client with transport-appropriate settings
        if self.config.transport_type == TransportType.TCP:
            # MCU host_timeout_ms = 3000ms — heartbeat must arrive well within that.
            # 1s gives a 3x safety margin and handles WiFi jitter without flooding.
            heartbeat_interval = 1.0   # 1 second - must be < MCU host_timeout_ms (3s)
            connection_timeout = 60.0  # Longer timeout for WiFi
            command_timeout = 5.0      # 5 seconds for WiFi latency
        else:
            heartbeat_interval = 0.5   # 500ms for serial/BLE (fast, reliable local links)
            connection_timeout = self.config.connection_timeout_s
            command_timeout = 1.0      # 1 second for serial

        self.client = MaraClient(
            self.transport,
            heartbeat_interval_s=heartbeat_interval,
            connection_timeout_s=connection_timeout,
            command_timeout_s=command_timeout,
            handshake_timeout_s=self.config.handshake_timeout_s,
            require_version_match=self.config.require_version_match,
            log_level=self.config.log_level,
            log_dir=self.config.log_dir,
            verbose=self.config.verbose,
        )

        # Start connection
        await self.client.start()

        # Return connection info from client properties
        return ConnectionInfo(
            transport_type=self.config.transport_type,
            firmware_version=self.client.firmware_version,
            protocol_version=self.client.protocol_version,
            board=self.client.board,
            platform_name=self.client.platform_name,
            features=self.client.features or [],
            capabilities=self.client.capabilities or 0,
        )

    async def disconnect(self) -> None:
        """Disconnect from the MCU."""
        if self.client:
            await self.client.stop()
            self.client = None

        if self.transport and hasattr(self.transport, 'stop'):
            import inspect
            stop_result = self.transport.stop()
            if inspect.isawaitable(stop_result):
                await stop_result
            self.transport = None

    def _create_transport(self):
        """Create the appropriate transport based on config."""
        if self.config.transport_type == TransportType.SERIAL:
            from mara_host.transport.serial_transport import SerialTransport
            return SerialTransport(
                self.config.port,
                baudrate=self.config.baudrate
            )

        elif self.config.transport_type == TransportType.BLE:
            from mara_host.transport.bluetooth_transport import BluetoothSerialTransport
            return BluetoothSerialTransport.auto(
                device_name=self.config.ble_name,
                baudrate=self.config.baudrate,
            )

        elif self.config.transport_type == TransportType.TCP:
            from mara_host.transport.tcp_transport import AsyncTcpTransport
            return AsyncTcpTransport(
                host=self.config.host,
                port=self.config.tcp_port
            )

        elif self.config.transport_type == TransportType.CAN:
            from mara_host.transport.can_transport import CANTransport
            return CANTransport(
                channel=self.config.can_channel,
                bustype=self.config.can_bustype,
                node_id=self.config.can_node_id,
            )

        else:
            raise ValueError(f"Unsupported transport type: {self.config.transport_type}")

    def on_event(self, topic: str, handler: Callable[[Any], None]) -> None:
        """
        Subscribe to an event topic.

        Args:
            topic: Event topic (e.g., "heartbeat", "telemetry.imu")
            handler: Callback function
        """
        if self.client:
            self.client.bus.subscribe(topic, handler)

    async def __aenter__(self) -> "ConnectionService":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self.client is not None and self.client._running
