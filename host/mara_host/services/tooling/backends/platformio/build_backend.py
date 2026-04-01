# services/build/backends/platformio/build_backend.py
"""PlatformIO implementation of the BuildBackend interface.

This is the ONLY file that knows how to translate MARA's BuildRequest
into ``pio run`` invocations.  Swap this adapter out and you swap
the entire build toolchain.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ..interfaces import BuildBackend
from ..models import BuildRequest, BuildOutcome


# Default firmware project path (same as build_firmware.py)
_DEFAULT_PROJECT = Path(__file__).resolve().parents[6] / "firmware" / "mcu"


def _find_pio() -> list[str]:
    """Return the command prefix to invoke PlatformIO."""
    pio = shutil.which("pio") or shutil.which("platformio")
    if pio:
        return [pio]
    return [sys.executable, "-m", "platformio"]


def _features_to_flags(features: dict[str, bool]) -> list[str]:
    """Convert feature dict to PlatformIO build flags."""
    flags = []
    for macro, enabled in features.items():
        flags.append(f"-D{macro}={int(enabled)}")
    return flags


def _parse_size_output(output: str) -> tuple[int | None, int | None]:
    """Parse firmware and RAM size from PlatformIO output.

    Returns (firmware_size, ram_usage) in bytes, or None if not found.
    """
    firmware_size = None
    ram_usage = None

    # Look for size summary lines like:
    # RAM:   [==        ]  18.5% (used 60696 bytes from 327680 bytes)
    # Flash: [====      ]  43.2% (used 849440 bytes from 1966080 bytes)
    ram_match = re.search(r"RAM:.*used\s+(\d+)\s+bytes", output)
    flash_match = re.search(r"Flash:.*used\s+(\d+)\s+bytes", output)

    if ram_match:
        ram_usage = int(ram_match.group(1))
    if flash_match:
        firmware_size = int(flash_match.group(1))

    return firmware_size, ram_usage


class PlatformIOBuildBackend(BuildBackend):
    """Compile firmware via PlatformIO's ``pio run``."""

    def build(self, request: BuildRequest) -> BuildOutcome:
        project_dir = request.project_dir or _DEFAULT_PROJECT

        cmd = _find_pio() + ["run", "-e", request.environment]
        if request.verbose:
            cmd.append("-v")

        # Set up environment with build flags
        env = os.environ.copy()
        if request.features:
            flags = _features_to_flags(request.features)
            flags_str = " ".join(flags)
            env["PLATFORMIO_BUILD_FLAGS"] = flags_str
            print(f"[pio-build] Build flags: {flags_str}")

        print(f"[pio-build] Running: {' '.join(cmd)}")

        if request.verbose:
            # In verbose mode, use Popen to stream output while capturing it
            process = subprocess.Popen(
                cmd,
                cwd=project_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output_lines = []
            for line in process.stdout:
                print(line, end="")  # Stream to console
                output_lines.append(line)
            process.wait()
            output = "".join(output_lines)
            error = ""
            return_code = process.returncode
        else:
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            output = result.stdout or ""
            error = result.stderr or ""
            return_code = result.returncode

        firmware_size, ram_usage = _parse_size_output(output)

        return BuildOutcome(
            success=return_code == 0,
            return_code=return_code,
            output=output,
            error=error,
            firmware_size=firmware_size,
            ram_usage=ram_usage,
        )

    def clean(self, environment: str | None = None) -> BuildOutcome:
        project_dir = _DEFAULT_PROJECT

        cmd = _find_pio() + ["run", "-t", "clean"]
        if environment:
            cmd.extend(["-e", environment])

        print(f"[pio-build] Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        return BuildOutcome(
            success=result.returncode == 0,
            return_code=result.returncode,
            output=result.stdout or "",
            error=result.stderr or "",
        )

    def get_version(self) -> str | None:
        """Return PlatformIO version string."""
        try:
            cmd = _find_pio() + ["--version"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Output is like "PlatformIO Core, version 6.1.11"
                return result.stdout.strip()
        except Exception:
            pass
        return None
