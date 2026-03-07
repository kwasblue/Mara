# mara_host/command/interfaces.py
"""Abstract interfaces for robot client operations."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any


class IMaraClient(ABC):
    """Abstract interface for MARA client operations."""

    @abstractmethod
    async def start(self) -> None:
        """Start the client and establish connection."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the client and close connection."""
        ...

    @abstractmethod
    async def send_reliable(
        self,
        type_str: str,
        payload: Optional[dict] = None,
        wait_for_ack: bool = True,
    ) -> tuple[bool, Optional[str]]:
        """
        Send a command with retry logic.

        Args:
            type_str: Command type (e.g., "CMD_ARM")
            payload: Optional command payload
            wait_for_ack: Whether to wait for acknowledgment

        Returns:
            (success, error_msg)
        """
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if client is connected."""
        ...


class ITransport(ABC):
    """Abstract interface for transport layer."""

    @abstractmethod
    async def send_bytes(self, data: bytes) -> None:
        """Send raw bytes over the transport."""
        ...

    @abstractmethod
    def set_frame_handler(self, handler: Any) -> None:
        """Set the callback for received frames."""
        ...

    @abstractmethod
    def start(self) -> Any:
        """Start the transport (may return awaitable)."""
        ...

    @abstractmethod
    def stop(self) -> Any:
        """Stop the transport (may return awaitable)."""
        ...
