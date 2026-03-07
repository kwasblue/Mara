from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Optional

from mara_host.core import protocol


class BaseTransport(ABC):
    """
    Base class for all transports. Handles:
      - registering a frame handler
      - encoding frames with the shared protocol
    Subclasses implement:
      - start()
      - stop()
      - _send_bytes()
    """

    def __init__(self) -> None:
        self._on_frame: Optional[Callable[[bytes], None]] = None

    def set_frame_handler(self, handler: Callable[[bytes], None]) -> None:
        self._on_frame = handler

    # Called by subclasses when a full body=[msg_type, payload...] is decoded
    def _handle_body(self, body: bytes) -> None:
        if self._on_frame:
            self._on_frame(body)

    def send_frame(self, msg_type: int, payload: bytes = b"") -> None:
        """Encode a frame and send it via the subclass implementation."""
        frame = protocol.encode(msg_type, payload)
        self._send_bytes(frame)

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def _send_bytes(self, data: bytes) -> None:
        ...
