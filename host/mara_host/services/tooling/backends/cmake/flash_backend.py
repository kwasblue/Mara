# services/build/backends/cmake/flash_backend.py
"""CMake/esptool implementation of the FlashBackend interface.

Uses esptool.py directly for flashing, or idf.py flash for ESP-IDF projects.
"""

from __future__ import annotations

import glob
import shutil
import subprocess
import sys
from pathlib import Path

from ..interfaces import FlashBackend
from ..models import FlashRequest, FlashOutcome


# Default firmware project path
_DEFAULT_PROJECT = Path(__file__).resolve().parents[6] / "firmware" / "mcu"


def _find_esptool() -> str | None:
    """Find esptool.py executable."""
    candidates = [
        shutil.which("esptool.py"),
        shutil.which("esptool"),
    ]
    # Check common installation paths
    home = Path.home()
    candidates.extend([
        str(home / ".local" / "bin" / "esptool.py"),
        str(home / ".espressif" / "python_env" / "idf5.0_py3.10_env" / "bin" / "esptool.py"),
    ])

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _find_idf_py() -> str | None:
    """Find idf.py for ESP-IDF projects."""
    return shutil.which("idf.py")


def _is_espidf_project(project_dir: Path) -> bool:
    """Check if this is an ESP-IDF project."""
    cmakelists = project_dir / "CMakeLists.txt"
    if not cmakelists.exists():
        return False
    try:
        content = cmakelists.read_text()
        return "idf_component_register" in content or "idf_build_process" in content
    except Exception:
        return False


class CMakeFlashBackend(FlashBackend):
    """Flash firmware via esptool or idf.py flash."""

    def __init__(self, build_dir: str = "build"):
        self.build_dir = build_dir

    def flash(self, request: FlashRequest) -> FlashOutcome:
        project_dir = request.project_dir or _DEFAULT_PROJECT

        # Check if this is an ESP-IDF project
        if _is_espidf_project(project_dir):
            return self._flash_espidf(request, project_dir)

        return self._flash_esptool(request, project_dir)

    def _flash_espidf(self, request: FlashRequest, project_dir: Path) -> FlashOutcome:
        """Flash using idf.py for ESP-IDF projects."""
        idf_py = _find_idf_py()
        if not idf_py:
            return FlashOutcome(
                success=False,
                return_code=1,
                error="idf.py not found. Is ESP-IDF installed and sourced?",
            )

        cmd = [idf_py]
        if request.port:
            cmd.extend(["-p", request.port])
        if request.baud != 115200:
            cmd.extend(["-b", str(request.baud)])
        cmd.append("flash")

        print(f"[cmake-flash] Running: {' '.join(cmd)}")
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

    def _flash_esptool(self, request: FlashRequest, project_dir: Path) -> FlashOutcome:
        """Flash using esptool directly."""
        esptool = _find_esptool()
        if not esptool:
            return FlashOutcome(
                success=False,
                return_code=1,
                error="esptool.py not found",
            )

        build_path = project_dir / self.build_dir

        # Find firmware binary
        firmware = None
        for pattern in ["*.bin", "**/*.bin"]:
            bins = list(build_path.glob(pattern))
            # Prefer files named firmware.bin, app.bin, or project name
            for b in bins:
                if b.name in ["firmware.bin", "app.bin", f"{project_dir.name}.bin"]:
                    firmware = b
                    break
            if firmware:
                break
            # Fall back to first .bin file
            if bins:
                firmware = bins[0]
                break

        if not firmware or not firmware.exists():
            return FlashOutcome(
                success=False,
                return_code=1,
                error=f"No firmware binary found in {build_path}",
            )

        # Find bootloader and partition table if they exist (ESP32)
        bootloader = build_path / "bootloader" / "bootloader.bin"
        partitions = build_path / "partition_table" / "partition-table.bin"

        # Build esptool command
        cmd = [sys.executable, esptool]
        cmd.extend(["--chip", "esp32"])
        if request.port:
            cmd.extend(["--port", request.port])
        cmd.extend(["--baud", str(request.baud)])
        cmd.extend(["--before", "default_reset"])
        cmd.extend(["--after", "hard_reset"])
        cmd.append("write_flash")
        cmd.append("-z")

        # Add flash addresses based on what files exist
        if bootloader.exists() and partitions.exists():
            # Full ESP32 flash with bootloader
            cmd.extend(["0x1000", str(bootloader)])
            cmd.extend(["0x8000", str(partitions)])
            cmd.extend(["0x10000", str(firmware)])
        else:
            # Simple firmware-only flash
            cmd.extend(["0x10000", str(firmware)])

        print(f"[cmake-flash] Running: {' '.join(cmd)}")
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

        return ports
