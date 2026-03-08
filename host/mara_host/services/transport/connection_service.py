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


class TransportType(Enum):
    """Supported transport types."""
    SERIAL = "serial"
    TCP = "tcp"
    CAN = "can"
    MQTT = "mqtt"


@dataclass
class ConnectionConfig:
    """Configuration for a robot connection."""
    transport_type: TransportType

    # Serial options
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200

    # TCP options
    host: str = "192.168.4.1"
    tcp_port: int = 3333

    # CAN options
    can_channel: str = "can0"
    can_bustype: str = "socketcan"
    can_node_id: int = 0

    # Client options
    connection_timeout_s: float = 6.0
    heartbeat_interval_s: float = 0.2
    require_version_match: bool = True

    # Logging options
    log_level: int = logging.INFO
    log_dir: str = "logs"


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
        self._event_handlers: dict[str, list[Callable]] = {}

    async def connect(self) -> ConnectionInfo:
        """
        Establish connection to the robot.

        Returns:
            ConnectionInfo with robot details
        """
        from mara_host.command.client import MaraClient

        # Create transport based on type
        self.transport = self._create_transport()

        # Create client
        self.client = MaraClient(
            self.transport,
            connection_timeout_s=self.config.connection_timeout_s,
            require_version_match=self.config.require_version_match,
            log_level=self.config.log_level,
            log_dir=self.config.log_dir,
        )

        # Start connection
        await self.client.start()

        # Return connection info
        identity = self.client.get_identity()
        return ConnectionInfo(
            transport_type=self.config.transport_type,
            firmware_version=identity.get("firmware"),
            protocol_version=identity.get("protocol"),
            board=identity.get("board"),
            platform_name=identity.get("name"),
            features=identity.get("features", []),
            capabilities=identity.get("capabilities", 0),
        )

    async def disconnect(self) -> None:
        """Disconnect from the MCU."""
        if self.client:
            await self.client.stop()
            self.client = None

        if self.transport and hasattr(self.transport, 'stop'):
            self.transport.stop()
            self.transport = None

    def _create_transport(self):
        """Create the appropriate transport based on config."""
        if self.config.transport_type == TransportType.SERIAL:
            from mara_host.transport.serial_transport import SerialTransport
            return SerialTransport(
                self.config.port,
                baudrate=self.config.baudrate
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

        # Also store for reconnection
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    async def __aenter__(self) -> "ConnectionService":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self.client is not None and self.client._running
