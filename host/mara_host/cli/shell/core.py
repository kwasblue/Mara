# mara_host/cli/commands/run/shell/core.py
"""Core interactive shell: REPL loop and connection management."""

import argparse
import shlex
from typing import Optional, Any

from .registry import get_commands
from mara_host.cli.console import console, print_success, print_error, print_info


class InteractiveShell:
    """Interactive command shell for robot control."""

    def __init__(
        self,
        event_log: list,
        default_args: argparse.Namespace,
        log_level: int,
        log_dir: str,
        setup_event_handlers,
        show_events_live: list,
    ):
        self.event_log = event_log
        self.default_args = default_args
        self.log_level = log_level
        self.log_dir = log_dir
        self.setup_event_handlers = setup_event_handlers
        self.show_events_live = show_events_live  # Mutable list for toggle

        # Current connection state
        self.client = None
        self.transport = None
        self.connected = False
        self.current_connection_info = ""

        # Commands are registered via decorator in command modules
        self.commands = get_commands()

    def require_connection(self) -> bool:
        """Check if connected, print error if not."""
        if not self.connected:
            print_error("Not connected. Use 'connect' first.")
            return False
        return True

    def print_success(self, msg: str) -> None:
        """Print success message."""
        print_success(msg)

    def print_error(self, msg: str) -> None:
        """Print error message."""
        print_error(msg)

    def print_info(self, msg: str) -> None:
        """Print info message."""
        print_info(msg)

    def _create_transport(self, transport_type: str, **kwargs):
        """Create a transport based on type and parameters."""
        if transport_type == "serial":
            from mara_host.transport.serial_transport import SerialTransport
            port = kwargs.get("port", self.default_args.port)
            baudrate = kwargs.get("baudrate", self.default_args.baudrate)
            return SerialTransport(port, baudrate=baudrate), f"serial:{port}"
        elif transport_type == "ble":
            from mara_host.transport.bluetooth_transport import BluetoothSerialTransport
            device_name = kwargs.get("device_name", self.default_args.ble_name)
            baudrate = kwargs.get("baudrate", self.default_args.baudrate)
            return BluetoothSerialTransport.auto(device_name=device_name, baudrate=baudrate), f"ble:{device_name}"
        else:  # tcp
            from mara_host.transport.tcp_transport import AsyncTcpTransport
            host = kwargs.get("host", self.default_args.host)
            port = kwargs.get("port", self.default_args.tcp_port)
            return AsyncTcpTransport(host=host, port=port), f"tcp:{host}:{port}"

    def _create_client(self, transport):
        """Create a client with the given transport."""
        from mara_host.command.client import MaraClient
        client = MaraClient(
            transport,
            # Disable timeout-based disconnect for interactive shell
            connection_timeout_s=float('inf'),
            # Very long command timeout for interactive shell
            command_timeout_s=10.0,
            max_retries=5,
            log_level=self.log_level,
            log_dir=self.log_dir,
        )
        self.setup_event_handlers(client)
        return client

    async def try_connect(self, transport_type: str = None, **kwargs) -> bool:
        """Try to connect with given or default parameters."""
        if self.connected:
            print_info("Already connected. Use 'disconnect' first.")
            return False

        # Use default transport type if not specified
        if transport_type is None:
            transport_type = self.default_args.transport

        try:
            self.transport, self.current_connection_info = self._create_transport(transport_type, **kwargs)
            self.client = self._create_client(self.transport)
            await self.client.start()
            self.connected = True
            print_success(f"Connected to robot ({self.current_connection_info})")
            return True
        except Exception as e:
            self.client = None
            self.transport = None
            self.connected = False
            print_info(f"Not connected: {e}")
            print_info("Use 'connect' to connect when device is ready")
            return False

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.connected and self.client:
            try:
                await self.client.stop()
            except Exception:
                pass
        if self.transport and hasattr(self.transport, 'stop'):
            try:
                self.transport.stop()
            except Exception:
                pass
        self.client = None
        self.transport = None
        self.connected = False

    async def execute(self, cmd_line: str) -> Optional[str]:
        """Execute a command line."""
        try:
            parts = shlex.split(cmd_line)
        except ValueError as e:
            print_error(f"Parse error: {e}")
            return None

        if not parts:
            return None

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in self.commands:
            handler, _ = self.commands[cmd]
            try:
                return await handler(self, args)
            except ValueError as e:
                print_error(f"Invalid argument: {e}")
                return None
            except (TypeError, IndexError) as e:
                print_error(f"Missing or invalid argument: {e}")
                return None
            except Exception as e:
                print_error(f"Command failed: {e}")
                return None
        else:
            print_error(f"Unknown command: {cmd}")
            console.print("[dim]Type 'help' for available commands[/dim]")
            return None
