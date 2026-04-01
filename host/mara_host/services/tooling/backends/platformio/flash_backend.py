# services/build/backends/platformio/flash_backend.py
"""PlatformIO implementation of the FlashBackend interface.

This is the ONLY file that knows how to translate MARA's FlashRequest
into ``pio run -t upload`` invocations.  Swap this adapter out and you swap
the entire flash toolchain.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..interfaces import FlashBackend
from ..models import FlashRequest, FlashOutcome


# Default firmware project path (same as build_firmware.py)
_DEFAULT_PROJECT = Path(__file__).resolve().parents[6] / "firmware" / "mcu"


def _find_pio() -> list[str]:
    """Return the command prefix to invoke PlatformIO."""
    pio = shutil.which("pio") or shutil.which("platformio")
    if pio:
        return [pio]
    return [sys.executable, "-m", "platformio"]


def _find_esptool() -> str | None:
    """Find a usable esptool entrypoint."""
    candidates = [
        shutil.which("esptool.py"),
        shutil.which("esptool"),
        str(Path.home() / ".platformio" / "packages" / "tool-esptoolpy" / "esptool.py"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


class PlatformIOFlashBackend(FlashBackend):
    """Flash firmware via PlatformIO's ``pio run -t upload``."""

    def flash(self, request: FlashRequest) -> FlashOutcome:
        project_dir = request.project_dir or _DEFAULT_PROJECT

        # Use direct esptool if requested or custom baud rate specified
        if (request.direct or request.baud != 115200) and request.port:
            return self._direct_flash(request, project_dir)

        cmd = _find_pio() + ["run", "-e", request.environment, "-t", "upload"]
        if request.port:
            cmd.extend(["--upload-port", request.port])
        if request.verbose:
            cmd.append("-v")

        print(f"[pio-flash] Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=not request.verbose,
            text=True,
        )

        output = ""
        error = ""
        if not request.verbose:
            output = result.stdout or ""
            error = result.stderr or ""

        return FlashOutcome(
            success=result.returncode == 0,
            return_code=result.returncode,
            output=output,
            error=error,
        )

    def _direct_flash(self, request: FlashRequest, project_dir: Path) -> FlashOutcome:
        """Flash via esptool directly using PlatformIO build artifacts.

        Allows custom baud rates for faster flashing.
        """
        build_dir = project_dir / ".pio" / "build" / request.environment
        bootloader = build_dir / "bootloader.bin"
        partitions = build_dir / "partitions.bin"
        firmware = build_dir / "firmware.bin"
        boot_app0 = (
            Path.home() / ".platformio" / "packages" /
            "framework-arduinoespressif32" / "tools" / "partitions" / "boot_app0.bin"
        )

        missing = [str(p) for p in (bootloader, partitions, firmware, boot_app0) if not p.exists()]
        if missing:
            return FlashOutcome(
                success=False,
                return_code=1,
                error=f"Missing flash artifacts: {', '.join(missing)}",
            )

        esptool = _find_esptool()
        if not esptool:
            return FlashOutcome(
                success=False,
                return_code=1,
                error="Could not find esptool",
            )

        cmd = [
            sys.executable, esptool,
            "--chip", "esp32",
            "--port", request.port,
            "--baud", str(request.baud),
            "--before", "default_reset",
            "--after", "hard_reset",
            "write_flash", "-z",
            "0x1000", str(bootloader),
            "0x8000", str(partitions),
            "0xe000", str(boot_app0),
            "0x10000", str(firmware),
        ]

        print(f"[pio-flash] Running direct flash: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=not request.verbose,
            text=True,
        )

        output = ""
        error = ""
        if not request.verbose:
            output = result.stdout or ""
            error = result.stderr or ""

        return FlashOutcome(
            success=result.returncode == 0,
            return_code=result.returncode,
            output=output,
            error=error,
        )

    def detect_devices(self) -> list[str]:
        """Return serial ports with connected ESP32 devices."""
        ports = []

        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                desc = (port.description or "").lower()
                hwid = (port.hwid or "").lower()

                # Check for common ESP32 USB-UART chips
                is_esp32 = any([
                    "cp210" in desc or "cp210" in hwid,
                    "ch340" in desc or "ch340" in hwid,
                    "ftdi" in desc or "ftdi" in hwid,
                    ("usb" in desc and "serial" in desc),
                ])

                if is_esp32:
                    ports.append(port.device)
        except ImportError:
            # Fallback: platform-specific glob patterns
            if sys.platform == "darwin":
                ports.extend(glob.glob("/dev/cu.usbserial-*"))
                ports.extend(glob.glob("/dev/cu.SLAB_USBtoUART*"))
            elif sys.platform == "linux":
                ports.extend(glob.glob("/dev/ttyUSB*"))
                ports.extend(glob.glob("/dev/ttyACM*"))
            elif sys.platform == "win32":
                # Windows COM ports - can't easily detect without pyserial
                pass

        return ports
