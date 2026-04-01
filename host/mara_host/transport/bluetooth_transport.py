from __future__ import annotations


from serial.tools import list_ports

from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE
from mara_host.transport.serial_transport import SerialTransport


class BluetoothSerialTransport(SerialTransport):
    """
    Bluetooth Classic SPP transport built on top of SerialTransport.

    From Python's perspective, this is still just a serial port.
    The main difference is we provide a convenience `auto()` constructor
    that tries to discover the correct /dev/cu.* device for a given
    Bluetooth SPP name (e.g., "ESP32-SPP").
    """

    def __init__(self, port: str, baudrate: int = DEFAULT_BAUDRATE) -> None:
        super().__init__(port=port, baudrate=baudrate)
        self.is_bluetooth = True  # purely informational

    @classmethod
    def auto(
        cls,
        device_name: str = "ESP32-SPP",
        baudrate: int = DEFAULT_BAUDRATE,
    ) -> "BluetoothSerialTransport":
        """
        Try to automatically find a Bluetooth SPP serial device whose
        description/name contains `device_name`.

        On macOS this usually ends up looking like:
            /dev/cu.ESP32-SPP
        or:
            /dev/cu.ESP32-SPP-1

        Raises RuntimeError if nothing is found.
        """
        target = device_name.lower()
        candidates: list[str] = []

        for port in list_ports.comports():
            desc = (port.description or "").lower()
            name = (port.name or "").lower()
            hwid = (port.hwid or "").lower()
            dev  = (port.device or "").lower()

            if (
                target in desc
                or target in name
                or target in hwid
                or target in dev
            ):
                # Prefer /dev/cu.* on macOS
                if port.device.startswith("/dev/cu."):
                    candidates.append(port.device)
                else:
                    candidates.append(port.device)

        if not candidates:
            raise RuntimeError(
                f"BluetoothSerialTransport.auto: no serial ports found for '{device_name}'"
            )

        # Pick first, or sort if you want stable ordering
        port = sorted(candidates)[0]
        print(f"[BluetoothSerialTransport] auto-selected port: {port}")

        return cls(port=port, baudrate=baudrate)
