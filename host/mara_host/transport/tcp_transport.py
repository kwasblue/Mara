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

    # Timeout for write operations (seconds)
    WRITE_TIMEOUT = 0.5

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

        # Serialize concurrent sends to prevent interleaved writes
        self._send_lock = asyncio.Lock()

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

    async def _drain_with_timeout(self) -> bool:
        """
        Drain the write buffer with a timeout.

        Returns True if drain succeeded, False if timed out or failed.
        On timeout, does NOT close the connection - just skips this write.
        The connection may still be usable for subsequent writes.
        """
        if not self._writer:
            return False
        try:
            await asyncio.wait_for(self._writer.drain(), timeout=self.WRITE_TIMEOUT)
            return True
        except asyncio.TimeoutError:
            # Don't close connection on timeout - just skip this drain
            # The TCP stack will eventually flush or the connection will die
            print("[TcpTransport] Write drain timeout (skipping)")
            return False
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            # Connection is dead, let read loop handle reconnect
            print(f"[TcpTransport] Connection error: {e}")
            return False
        except Exception as e:
            print(f"[TcpTransport] Write error: {e}")
            return False

    async def send_frame(self, msg_type: int, payload: bytes = b"", drain: bool = False) -> None:
        """
        Encode a frame using your existing protocol and send it.
        Typically used if you want the transport to handle framing.

        Args:
            msg_type: Protocol message type
            payload: Frame payload
            drain: If True, wait for buffer to flush. If False, just buffer (default).
        """
        if not self._writer:
            return

        frame = protocol.encode(msg_type, payload)
        async with self._send_lock:
            if not self._writer:
                return
            self._writer.write(frame)
            if drain:
                await self._drain_with_timeout()

    async def send_bytes(self, data: bytes, drain: bool = False) -> None:
        """
        Send already-encoded bytes over the socket.

        This is what MaraClient expects to call, since it often
        builds the full frame itself (e.g. protocol.encode_json_cmd(...)).

        Args:
            data: Bytes to send
            drain: If True, wait for buffer to flush (slower but confirms delivery).
                   If False, just buffer the write (fast, like serial).
        """
        if not self._writer:
            return

        async with self._send_lock:
            if not self._writer:
                return
            self._writer.write(data)
            if drain:
                await self._drain_with_timeout()

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

            # Platform-specific keepalive settings (aggressive for WiFi)
            if sys.platform == 'darwin':  # macOS
                # TCP_KEEPALIVE = idle time before sending keepalive probes
                TCP_KEEPALIVE = 0x10
                sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 10)  # 10 seconds
            elif sys.platform == 'linux':
                # Idle time, interval between probes, max failed probes
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)  # 10 seconds
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)   # 5 seconds between probes
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
