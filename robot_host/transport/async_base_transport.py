# robot_host/transport/async_base_transport.py
"""
Abstract base class for async transports.

Async transports handle communication with robots over async I/O
(TCP, MQTT, WebSockets, etc).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional


class AsyncBaseTransport(ABC):
    """
    Abstract base class for all async transports.

    Async transports implement the HasSendBytes protocol and provide:
    - Async lifecycle (start/stop)
    - Async send_bytes for transmitting data
    - Frame handler registration for receiving data

    Subclasses must implement:
        - start(): Connect and begin receiving
        - stop(): Disconnect and cleanup
        - send_bytes(): Send raw bytes to the robot

    Example:
        class MyTransport(AsyncBaseTransport):
            async def start(self) -> None:
                await self._connect()

            async def stop(self) -> None:
                await self._disconnect()

            async def send_bytes(self, data: bytes) -> None:
                await self._connection.write(data)
    """

    def __init__(self) -> None:
        self._frame_handler: Optional[Callable[[bytes], None]] = None

    def set_frame_handler(self, handler: Callable[[bytes], None]) -> None:
        """
        Register a callback for incoming frames.

        The handler receives the frame body (msg_type + payload bytes).
        Called by the client to receive responses and telemetry.

        Args:
            handler: Callback function that receives frame bytes
        """
        self._frame_handler = handler

    def _handle_frame(self, body: bytes) -> None:
        """
        Dispatch a received frame to the registered handler.

        Call this from subclass when a complete frame is received.

        Args:
            body: Frame body bytes (msg_type + payload)
        """
        if self._frame_handler:
            self._frame_handler(body)

    @abstractmethod
    async def start(self) -> None:
        """
        Start the transport connection.

        Must establish connection and begin receiving data.
        Should be idempotent (safe to call multiple times).
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the transport connection.

        Must close connection and cleanup resources.
        Should be idempotent (safe to call multiple times).
        """
        ...

    @abstractmethod
    async def send_bytes(self, data: bytes) -> None:
        """
        Send raw bytes over the transport.

        Args:
            data: Bytes to send (typically a framed message)

        Raises:
            RuntimeError: If transport is not connected
        """
        ...

    @property
    def is_connected(self) -> bool:
        """
        Check if transport is currently connected.

        Override in subclass to provide actual connection state.
        """
        return False
