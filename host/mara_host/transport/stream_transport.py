# mara_host/transports/stream_transport.py
from __future__ import annotations
import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from mara_host.core import protocol
from mara_host.transport.base_transport import BaseTransport

_log = logging.getLogger(__name__)


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
        return self._is_open

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

        # Shutdown write executor (cancel pending writes to avoid hang)
        if self._write_executor is not None:
            try:
                # Python 3.9+: cancel_futures=True prevents hanging on stuck writes
                import sys
                if sys.version_info >= (3, 9):
                    self._write_executor.shutdown(wait=False, cancel_futures=True)
                else:
                    self._write_executor.shutdown(wait=False)
            except Exception as e:
                _log.warning("Error shutting down write executor: %s", e)
            finally:
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
    # Maximum consecutive errors before stopping reader (prevents infinite error loops)
    _MAX_CONSECUTIVE_ERRORS = 5

    def _reader_loop(self) -> None:
        """
        Background reader thread that processes incoming data.

        Threading note on _rx_buffer:
        _rx_buffer is only written and consumed by this reader thread - there's
        no concurrent access from send_bytes. The frame handlers invoked via
        _safe_handle_body may trigger reply sends, but those go through
        send_bytes which uses _async_lock + executor, properly serialized.
        """
        consecutive_errors = 0

        while not self._stop:
            try:
                data = self._read_raw(256)
                if data:
                    consecutive_errors = 0  # Reset on successful read
                    self._rx_buffer.extend(data)
                    protocol.extract_frames(self._rx_buffer, self._safe_handle_body)
                else:
                    time.sleep(0.01)
            except Exception as e:
                consecutive_errors += 1
                _log.warning(
                    "Reader loop error (%d/%d): %s",
                    consecutive_errors, self._MAX_CONSECUTIVE_ERRORS, e
                )
                if consecutive_errors >= self._MAX_CONSECUTIVE_ERRORS:
                    _log.error("Too many consecutive reader errors, stopping reader loop")
                    self._stop = True
                    break
                time.sleep(0.5)

    def _safe_handle_body(self, body: bytes) -> None:
        """Wrap frame handler to catch and log exceptions."""
        try:
            self._handle_body(body)
        except Exception as e:
            _log.error("Frame handler error: %s", e, exc_info=True)

    # ---- async-friendly write API ----
    async def send_bytes(self, data: bytes) -> None:
        """
        Send bytes with asyncio coordination.

        Uses asyncio.Lock to serialize async callers (no thread overhead),
        then delegates actual I/O to a dedicated executor thread.

        NOTE: Race window with stop()
        There's a narrow window where send_bytes reads _cached_loop, then stop()
        clears it and closes the transport, then send_bytes proceeds with the
        stale loop reference. This is harmless in practice because the _is_open
        check under _async_lock will catch it, but the error message may be
        misleading ("Transport not open" rather than "Transport stopped").
        """
        # Fast path: cache loop reference to avoid get_running_loop() overhead
        # Validate loop is still running, not just not-closed
        loop = self._cached_loop
        try:
            if loop is None or loop.is_closed() or not loop.is_running():
                loop = asyncio.get_running_loop()
                self._cached_loop = loop
        except RuntimeError:
            # No running loop - this shouldn't happen in async context
            raise RuntimeError("send_bytes called outside async context")

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
