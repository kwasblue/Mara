from __future__ import annotations
import time
from typing import Optional

import serial

from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE
from mara_host.transport.stream_transport import StreamTransport


class SerialTransport(StreamTransport):
    """
    Generic serial transport for USB/UART or Bluetooth-Serial devices.
    'port' is something like:
      - macOS USB:   /dev/tty.usbserial-XXXX  or  /dev/tty.usbmodemXXXX
      - macOS BT:    /dev/tty.YOUR_BT_DEVICE-XXX
      - Linux USB:   /dev/ttyUSB0, /dev/ttyACM0
      - Linux BT:    /dev/rfcomm0
      - Windows:     COM3, COM5, ...
    """

    def __init__(self, port: str, baudrate: int = DEFAULT_BAUDRATE) -> None:
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self._ser: Optional[serial.Serial] = None

    def _open(self) -> None:
        kwargs = dict(timeout=0.05, write_timeout=0.2)
        try:
            # POSIX-only; helps detect “port still open elsewhere”
            kwargs["exclusive"] = True
        except Exception:
            pass

        self._ser = serial.Serial(self.port, self.baudrate, **kwargs)
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
        except Exception:
            pass

        # Brief stabilization delay for macOS USB serial drivers
        time.sleep(0.1)

    def _close(self) -> None:
        if not self._ser:
            return

        try:
            # Unblock any pending read/write in another thread
            if hasattr(self._ser, "cancel_read"):
                self._ser.cancel_read()
            if hasattr(self._ser, "cancel_write"):
                self._ser.cancel_write()
        except Exception:
            pass

        try:
            if self._ser.is_open:
                self._ser.close()
        finally:
            self._ser = None


    def _read_raw(self, n: int) -> bytes:
        if not self._ser:
            return b""
        try:
            return self._ser.read(n)
        except serial.SerialException as e:
            # Handle transient "device reports readiness" errors on macOS.
            # This is a known pyserial issue on macOS where USB serial devices
            # report ready but return no data. The error message check is fragile
            # and depends on pyserial's error string (tested with pyserial 3.5).
            # If pyserial changes this message, errors will propagate to _reader_loop
            # and count toward MAX_CONSECUTIVE_ERRORS, potentially causing disconnect.
            if "returned no data" in str(e):
                time.sleep(0.05)
                return b""
            raise

    def _send_bytes(self, data: bytes) -> None:
        if not self._ser or not self._ser.is_open:
            raise RuntimeError("Serial not open")
        self._ser.write(data)
