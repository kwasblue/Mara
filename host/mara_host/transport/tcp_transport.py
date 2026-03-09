import asyncio
from typing import Optional

from mara_host.core import protocol
from mara_host.transport.async_base_transport import AsyncBaseTransport


class AsyncTcpTransport(AsyncBaseTransport):
    """
    Async TCP transport.

    Features:
      - Maintains a connection to (host, port)
      - Reconnects on failure
      - Reads bytes from the socket, then uses protocol.extract_frames()
        to turn them into framed messages
      - Calls frame handler with body (msg_type + payload)
    """

    def __init__(
        self,
        host: str,
        port: int,
        reconnect_delay: float = 1.0,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.reconnect_delay = reconnect_delay

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._rx_buffer = bytearray()

    @property
    def is_connected(self) -> bool:
        """Check if transport is currently connected."""
        return self._writer is not None

    async def start(self) -> None:
        """Start connection/reconnect loop in the background."""
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop background loop and close the socket."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def send_frame(self, msg_type: int, payload: bytes = b"") -> None:
        """
        Encode a frame using your existing protocol and send it.
        Typically used if you want the transport to handle framing.
        """
        if not self._writer:
            print("[TcpTransport] send_frame called while not connected")
            return

        frame = protocol.encode(msg_type, payload)
        self._writer.write(frame)
        await self._writer.drain()

    async def send_bytes(self, data: bytes) -> None:
        """
        Send already-encoded bytes over the socket.

        This is what MaraClient expects to call, since it often
        builds the full frame itself (e.g. protocol.encode_json_cmd(...)).
        """
        if not self._writer:
            print("[TcpTransport] send_bytes called while not connected")
            return

        self._writer.write(data)
        await self._writer.drain()

    # Optional alias if you ever called `send()` elsewhere
    async def send(self, data: bytes) -> None:
        await self.send_bytes(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _configure_socket_keepalive(self) -> None:
        """Configure TCP keepalive for connection stability over WiFi."""
        import socket
        import sys

        if not self._writer:
            return

        try:
            sock = self._writer.get_extra_info('socket')
            if sock is None:
                return

            # Enable keepalive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Platform-specific keepalive settings
            if sys.platform == 'darwin':  # macOS
                # TCP_KEEPALIVE = idle time before sending keepalive probes
                TCP_KEEPALIVE = 0x10
                sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 30)
            elif sys.platform == 'linux':
                # Idle time, interval between probes, max failed probes
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            # Disable Nagle's algorithm for lower latency
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        except Exception as e:
            print(f"[TcpTransport] Could not set socket options: {e}")

    # ------------------------------------------------------------------
    # Internal async loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Main reconnect + read loop."""
        while self._running:
            try:
                print(f"[TcpTransport] Connecting to {self.host}:{self.port} ...")
                self._reader, self._writer = await asyncio.open_connection(
                    self.host, self.port
                )
                print("[TcpTransport] Connected")

                # Enable TCP keepalive for connection stability
                self._configure_socket_keepalive()

                # Clear buffer on (re)connect
                self._rx_buffer.clear()

                # Read loop
                while self._running:
                    data = await self._reader.read(1024)
                    if not data:
                        print("[TcpTransport] Connection closed by peer")
                        break

                    # Accumulate and let protocol.extract_frames parse frames.
                    self._rx_buffer.extend(data)

                    # This will call self._frame_handler(body) for each frame found.
                    protocol.extract_frames(self._rx_buffer, self._frame_handler)

            except Exception as e:
                print(f"[TcpTransport] Error: {e}")

            # Cleanup and reconnect delay
            if self._writer:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:
                    pass
                self._writer = None
                self._reader = None

            if self._running:
                print(f"[TcpTransport] Reconnecting in {self.reconnect_delay}s ...")
                await asyncio.sleep(self.reconnect_delay)
