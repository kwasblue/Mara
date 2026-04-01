# services/tooling/device_service.py
"""Device discovery and management service.

This is a MARA-owned abstraction for device detection and info.
It does NOT depend on any specific build tool or framework.
"""

from __future__ import annotations

import glob
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ChipType(str, Enum):
    """Known microcontroller chip types."""
    ESP32 = "esp32"
    ESP32_S2 = "esp32s2"
    ESP32_S3 = "esp32s3"
    ESP32_C3 = "esp32c3"
    STM32 = "stm32"
    RP2040 = "rp2040"
    UNKNOWN = "unknown"


class UsbChip(str, Enum):
    """USB-UART bridge chip types."""
    CP2102 = "CP2102/CP2104"
    CH340 = "CH340"
    FTDI = "FTDI"
    CDC = "USB CDC"
    UNKNOWN = "Unknown"


@dataclass
class DeviceInfo:
    """Information about a detected device."""
    port: str
    usb_chip: UsbChip = UsbChip.UNKNOWN
    mcu_chip: ChipType = ChipType.UNKNOWN
    description: str = ""
    hwid: str = ""
    manufacturer: str = ""
    product: str = ""
    serial_number: str = ""

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "usb_chip": self.usb_chip.value,
            "mcu_chip": self.mcu_chip.value,
            "description": self.description,
            "hwid": self.hwid,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "serial_number": self.serial_number,
        }


class DeviceService:
    """Service for device discovery and management.

    This is the single source of truth for device operations.
    CLI and GUI should use this instead of direct serial port access.
    """

    def detect_devices(self, chip_filter: Optional[ChipType] = None) -> list[DeviceInfo]:
        """Detect connected devices.

        Args:
            chip_filter: If specified, only return devices matching this chip type.

        Returns:
            List of detected devices.
        """
        devices = []

        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                device = self._analyze_port(port)
                if device:
                    if chip_filter is None or device.mcu_chip == chip_filter:
                        devices.append(device)
        except ImportError:
            # Fallback: platform-specific detection
            devices = self._fallback_detection()
            if chip_filter:
                devices = [d for d in devices if d.mcu_chip == chip_filter]

        return devices

    def detect_esp32_devices(self) -> list[DeviceInfo]:
        """Convenience method to detect ESP32 family devices."""
        devices = self.detect_devices()
        esp32_chips = {ChipType.ESP32, ChipType.ESP32_S2, ChipType.ESP32_S3, ChipType.ESP32_C3}
        return [d for d in devices if d.mcu_chip in esp32_chips or d.mcu_chip == ChipType.UNKNOWN]

    def get_device_info(self, port: str) -> Optional[DeviceInfo]:
        """Get detailed info for a specific port."""
        devices = self.detect_devices()
        for d in devices:
            if d.port == port:
                return d
        return None

    def get_chip_info(self, port: str) -> Optional[dict]:
        """Query chip info directly from the device.

        This uses esptool to read chip ID and other info.
        """
        esptool = self._find_esptool()
        if not esptool:
            return None

        try:
            cmd = [sys.executable, esptool, "--port", port, "chip_id"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return self._parse_chip_info(result.stdout)
        except (subprocess.TimeoutExpired, Exception):
            pass
        return None

    def erase_flash(self, port: str) -> tuple[bool, str]:
        """Erase device flash memory.

        Returns:
            (success, message)
        """
        esptool = self._find_esptool()
        if not esptool:
            return False, "esptool not found"

        try:
            cmd = [sys.executable, esptool, "--port", port, "erase_flash"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return True, "Flash erased successfully"
            return False, result.stderr or "Erase failed"
        except subprocess.TimeoutExpired:
            return False, "Erase timed out"
        except Exception as e:
            return False, str(e)

    def _analyze_port(self, port) -> Optional[DeviceInfo]:
        """Analyze a serial port and create DeviceInfo."""
        desc = (port.description or "").lower()
        hwid = (port.hwid or "").lower()

        # Detect USB-UART chip
        usb_chip = UsbChip.UNKNOWN
        if "cp210" in desc or "cp210" in hwid:
            usb_chip = UsbChip.CP2102
        elif "ch340" in desc or "ch340" in hwid:
            usb_chip = UsbChip.CH340
        elif "ftdi" in desc or "ftdi" in hwid:
            usb_chip = UsbChip.FTDI
        elif "cdc" in desc or ("usb" in desc and "serial" in desc):
            usb_chip = UsbChip.CDC

        # Filter: only include likely microcontroller ports
        if usb_chip == UsbChip.UNKNOWN:
            # Check for other patterns that suggest a dev board
            if not any(x in desc for x in ["serial", "uart", "usb"]):
                return None

        # Infer MCU type (best guess without querying device)
        mcu_chip = ChipType.UNKNOWN
        if "esp32" in desc or "esp32" in hwid:
            mcu_chip = ChipType.ESP32
        elif usb_chip in {UsbChip.CP2102, UsbChip.CH340}:
            # These are commonly used with ESP32
            mcu_chip = ChipType.ESP32

        return DeviceInfo(
            port=port.device,
            usb_chip=usb_chip,
            mcu_chip=mcu_chip,
            description=port.description or "",
            hwid=port.hwid or "",
            manufacturer=getattr(port, 'manufacturer', '') or "",
            product=getattr(port, 'product', '') or "",
            serial_number=getattr(port, 'serial_number', '') or "",
        )

    def _fallback_detection(self) -> list[DeviceInfo]:
        """Platform-specific fallback detection without pyserial."""
        devices = []

        if sys.platform == "darwin":
            patterns = ["/dev/cu.usbserial-*", "/dev/cu.SLAB_USBtoUART*", "/dev/cu.wchusbserial*"]
        elif sys.platform == "linux":
            patterns = ["/dev/ttyUSB*", "/dev/ttyACM*"]
        elif sys.platform == "win32":
            # Windows: can't easily detect without pyserial
            return []
        else:
            return []

        for pattern in patterns:
            for port in glob.glob(pattern):
                devices.append(DeviceInfo(
                    port=port,
                    usb_chip=UsbChip.UNKNOWN,
                    mcu_chip=ChipType.UNKNOWN,
                    description="USB Serial",
                ))

        return devices

    def _find_esptool(self) -> Optional[str]:
        """Find esptool executable."""
        candidates = [
            shutil.which("esptool.py"),
            shutil.which("esptool"),
        ]
        # Check common paths
        home = Path.home()
        candidates.extend([
            str(home / ".local" / "bin" / "esptool.py"),
            str(home / ".platformio" / "packages" / "tool-esptoolpy" / "esptool.py"),
        ])

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return None

    def _parse_chip_info(self, output: str) -> dict:
        """Parse esptool chip_id output."""
        info = {}
        for line in output.split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                if key and value:
                    info[key] = value
        return info
