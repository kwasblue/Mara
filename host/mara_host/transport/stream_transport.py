# mara_host/transports/stream_transport.py
from __future__ import annotations
import asyncio
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from mara_host.core import protocol
from mara_host.transport.base_transport import BaseTransport


class StreamTransport(BaseTransport, ABC):
    def __init__(self) -> None:
        super().__init__()
        self._rx_buffer = bytearray()
        self._stop = False
        self._thread: Optional[threading.Thread] = None

        # Protect close vs writes
        self._io_lock = threading.Lock()
        self._is_open = False

        # Async coordination lock (no thread overhead for async callers)
        self._async_lock = asyncio.Lock()

        # Dedicated write executor (reuse single thread, don't spawn per call)
        self._write_executor: Optional[ThreadPoolExecutor] = None

        # Cached event loop reference (avoid get_running_loop() per call)
        self._cached_loop: Optional[asyncio.AbstractEventLoop] = None

    # ---- subclass hooks ----
    @abstractmethod
    def _open(self) -> None: ...

    @abstractmethod
    def _close(self) -> None: ...

    @abstractmethod
    def _read_raw(self, n: int) -> bytes: ...

    @abstractmethod
    def _send_bytes(self, data: bytes) -> None: ...

    # ---- helpers ----
    def is_open(self) -> bool:
        return bool(self._ser and self._ser.is_open)

    # ---- sync lifecycle ----
    def start(self) -> None:
        # Make start idempotent-ish
        if self._is_open:
            return

        self._stop = False
        self._rx_buffer.clear()
        with self._io_lock:
            self._open()
            self._is_open = True

        # Create dedicated executor for serial writes (single thread, reused)
        self._write_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="mara_write"
        )

        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        # Make stop idempotent
        self._stop = True

        t = self._thread
        if t and t.is_alive():
            t.join(timeout=2.0)
        self._thread = None

        # Shutdown write executor
        if self._write_executor is not None:
            self._write_executor.shutdown(wait=True)
            self._write_executor = None

        # Clear cached loop reference
        self._cached_loop = None

        # Ensure nobody is writing while we close
        with self._io_lock:
            if self._is_open:
                try:
                    self._close()
                finally:
                    self._is_open = False

        # Tiny settle helps macOS/USB churn a lot
        time.sleep(0.05)

    # ---- background reader ----
    def _reader_loop(self) -> None:
        while not self._stop:
            try:
                data = self._read_raw(256)
                if data:
                    self._rx_buffer.extend(data)
                    protocol.extract_frames(self._rx_buffer, lambda body: self._handle_body(body))
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[StreamTransport] error: {e}")
                time.sleep(0.5)

    # ---- async-friendly write API ----
    async def send_bytes(self, data: bytes) -> None:
        """
        Send bytes with asyncio coordination.

        Uses asyncio.Lock to serialize async callers (no thread overhead),
        then delegates actual I/O to a dedicated executor thread.
        """
        # Fast path: cache loop reference to avoid get_running_loop() overhead
        loop = self._cached_loop
        if loop is None or loop.is_closed():
            loop = asyncio.get_running_loop()
            self._cached_loop = loop

        # asyncio.Lock serializes async callers without thread overhead
        async with self._async_lock:
            if not self._is_open or self._stop:
                raise RuntimeError("Transport not open")

            # Use dedicated executor (single thread, reused)
            executor = self._write_executor
            if executor is None:
                raise RuntimeError("Transport not open")

            await loop.run_in_executor(executor, self._send_bytes_sync, data)

    def _send_bytes_sync(self, data: bytes) -> None:
        """Synchronous send with I/O lock protection."""
        with self._io_lock:
            if not self._is_open or self._stop:
                raise RuntimeError("Transport not open")
            self._send_bytes(data)
