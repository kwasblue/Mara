import asyncio
from typing import Callable, Optional

class FakeTransport:
    def __init__(self):
        self._handler: Optional[Callable[[bytes], None]] = None
        self.sent: list[bytes] = []
        self.started = False
        self.stopped = False

    def set_frame_handler(self, handler: Callable[[bytes], None]) -> None:
        self._handler = handler

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    async def send_bytes(self, data: bytes) -> None:
        # capture what the client sends (already fully framed bytes)
        self.sent.append(data)

    # --- test helper ---
    async def inject_body(self, body: bytes) -> None:
        # body is what StreamTransport would pass up:
        # first byte msg_type, rest payload
        if self._handler:
            self._handler(body)
        await asyncio.sleep(0)  # yield to event loop
