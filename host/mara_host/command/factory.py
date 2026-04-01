# mara_host/command/factory.py
"""
Factory for creating MARA clients with various transports.

Eliminates 15+ duplicate client creation blocks across the codebase.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, TYPE_CHECKING
import logging
import sys

from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE


def _default_serial_port() -> str:
    if sys.platform.startswith("linux"):
        return "/dev/ttyUSB0"
    elif sys.platform == "darwin":
        return "/dev/cu.usbserial-0001"
    return "COM3"

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient
    from mara_host.core.event_bus import EventBus


@dataclass
class ClientConfig:
    """Configuration for MARA client creation."""

    connection_timeout_s: float = 6.0
    heartbeat_interval_s: float = 0.2
    command_timeout_s: float = 0.25
    max_retries: int = 3
    require_version_match: bool = True
    handshake_timeout_s: float = 2.0
    log_level: int = logging.INFO
    log_dir: str = "logs"


class MaraClientFactory:
    """
    Factory to eliminate duplicate client creation blocks.

    Usage:
        factory = MaraClientFactory()

        # Create serial client
        client = factory.create_serial_client("/dev/cu.usbserial-0001")

        # Create TCP client
        client = factory.create_tcp_client("192.168.4.1", port=3333)

        # Create from argparse args
        client = factory.from_args(args)
    """

    def __init__(self, bus: Optional["EventBus"] = None):
        """
        Initialize factory with optional shared event bus.

        Args:
            bus: Optional shared EventBus instance
        """
        self._bus = bus

    def create_serial_client(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        config: Optional[ClientConfig] = None,
        bus: Optional["EventBus"] = None,
    ) -> "MaraClient":
        """
        Create a serial transport client.

        Args:
            port: Serial port path (e.g., "/dev/cu.usbserial-0001")
            baudrate: Baud rate (default: 921600)
            config: Optional client configuration
            bus: Optional event bus override

        Returns:
            Configured MaraClient
        """
        from mara_host.command.client import MaraClient
        from mara_host.transport.serial_transport import SerialTransport

        config = config or ClientConfig()
        transport = SerialTransport(port, baudrate=baudrate)

        return MaraClient(
            transport=transport,
            bus=bus or self._bus,
            heartbeat_interval_s=config.heartbeat_interval_s,
            connection_timeout_s=config.connection_timeout_s,
            command_timeout_s=config.command_timeout_s,
            max_retries=config.max_retries,
            require_version_match=config.require_version_match,
            handshake_timeout_s=config.handshake_timeout_s,
            log_level=config.log_level,
            log_dir=config.log_dir,
        )

    def create_tcp_client(
        self,
        host: str,
        port: int = 3333,
        config: Optional[ClientConfig] = None,
        bus: Optional["EventBus"] = None,
    ) -> "MaraClient":
        """
        Create a TCP transport client.

        Args:
            host: TCP host address (e.g., "192.168.4.1")
            port: TCP port (default: 3333)
            config: Optional client configuration
            bus: Optional event bus override

        Returns:
            Configured MaraClient
        """
        from mara_host.command.client import MaraClient
        from mara_host.transport.tcp_transport import AsyncTcpTransport

        config = config or ClientConfig()
        transport = AsyncTcpTransport(host=host, port=port)

        return MaraClient(
            transport=transport,
            bus=bus or self._bus,
            heartbeat_interval_s=config.heartbeat_interval_s,
            connection_timeout_s=config.connection_timeout_s,
            command_timeout_s=config.command_timeout_s,
            max_retries=config.max_retries,
            require_version_match=config.require_version_match,
            handshake_timeout_s=config.handshake_timeout_s,
            log_level=config.log_level,
            log_dir=config.log_dir,
        )

    def create_can_client(
        self,
        channel: str = "can0",
        bustype: str = "socketcan",
        node_id: int = 0,
        virtual: bool = False,
        config: Optional[ClientConfig] = None,
        bus: Optional["EventBus"] = None,
    ) -> "MaraClient":
        """
        Create a CAN transport client.

        Args:
            channel: CAN interface name (default: "can0")
            bustype: CAN bus type (default: "socketcan")
            node_id: Local node ID 0-14 (default: 0)
            virtual: Use virtual CAN for testing
            config: Optional client configuration
            bus: Optional event bus override

        Returns:
            Configured MaraClient

        Raises:
            ImportError: If python-can is not installed
        """
        from mara_host.command.client import MaraClient
        from mara_host.transport.can_transport import CANTransport, VirtualCANTransport

        config = config or ClientConfig()

        if virtual:
            transport = VirtualCANTransport(channel=channel, node_id=node_id)
        else:
            transport = CANTransport(
                channel=channel,
                bustype=bustype,
                node_id=node_id,
            )

        return MaraClient(
            transport=transport,
            bus=bus or self._bus,
            heartbeat_interval_s=config.heartbeat_interval_s,
            connection_timeout_s=config.connection_timeout_s,
            command_timeout_s=config.command_timeout_s,
            max_retries=config.max_retries,
            require_version_match=config.require_version_match,
            handshake_timeout_s=config.handshake_timeout_s,
            log_level=config.log_level,
            log_dir=config.log_dir,
        )

    def from_args(
        self,
        args: Any,
        config: Optional[ClientConfig] = None,
        bus: Optional["EventBus"] = None,
    ) -> "MaraClient":
        """
        Create client from argparse args (CLI commands).

        Detects transport type from args:
        - args.tcp set -> TCP client
        - args.channel set -> CAN client
        - Otherwise -> Serial client

        Args:
            args: Parsed argparse.Namespace
            config: Optional client configuration
            bus: Optional event bus override

        Returns:
            Configured MaraClient
        """
        # Build config from args if not provided
        if config is None:
            config = ClientConfig()
            # Pull logging args if present
            if hasattr(args, "log_level") and args.log_level:
                level_map = {
                    "debug": logging.DEBUG,
                    "info": logging.INFO,
                    "warning": logging.WARNING,
                    "error": logging.ERROR,
                }
                config.log_level = level_map.get(args.log_level, logging.INFO)
            if hasattr(args, "log_dir") and args.log_dir:
                config.log_dir = args.log_dir

        # Detect transport type
        if getattr(args, "tcp", None):
            return self.create_tcp_client(
                host=args.tcp,
                port=getattr(args, "tcp_port", 3333),
                config=config,
                bus=bus,
            )

        if hasattr(args, "channel"):
            return self.create_can_client(
                channel=getattr(args, "channel", "can0"),
                bustype=getattr(args, "bustype", "socketcan"),
                node_id=getattr(args, "node_id", 0),
                virtual=getattr(args, "virtual", False),
                config=config,
                bus=bus,
            )

        # Default: serial
        return self.create_serial_client(
            port=getattr(args, "port", None) or _default_serial_port(),
            baudrate=getattr(args, "baudrate", DEFAULT_BAUDRATE),
            config=config,
            bus=bus,
        )


# Convenience function for CLI commands
def create_client_from_args(
    args: Any,
    config: Optional[ClientConfig] = None,
    bus: Optional["EventBus"] = None,
) -> "MaraClient":
    """
    Convenience function for CLI commands.

    Usage:
        from mara_host.command.factory import create_client_from_args

        client = create_client_from_args(args)
        await client.start()
        # ... use client ...
        await client.stop()

    Args:
        args: Parsed argparse.Namespace
        config: Optional client configuration
        bus: Optional event bus

    Returns:
        Configured MaraClient
    """
    return MaraClientFactory(bus).from_args(args, config)
