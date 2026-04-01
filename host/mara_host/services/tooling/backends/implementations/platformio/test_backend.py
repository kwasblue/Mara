# services/build/backends/platformio/test_backend.py
"""PlatformIO implementation of the TestBackend interface.

This is the ONLY file that knows how to translate MARA's TestRequest
into ``pio test`` invocations.  Swap this adapter out and you swap
the entire test toolchain.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ...interfaces import TestBackend
from ...models import TestEnvironment, TestRequest, TestOutcome


# Default firmware project path (same as build_firmware.py)
_DEFAULT_PROJECT = Path(__file__).resolve().parents[7] / "firmware" / "mcu"

# Map MARA-level environment names to PlatformIO environment names
_ENV_MAP: dict[TestEnvironment, str] = {
    TestEnvironment.NATIVE: "native",
    TestEnvironment.DEVICE: "esp32_test",
}


def _find_pio() -> list[str]:
    """Return the command prefix to invoke PlatformIO."""
    pio = shutil.which("pio") or shutil.which("platformio")
    if pio:
        return [pio]
    return [sys.executable, "-m", "platformio"]


class PlatformIOTestBackend(TestBackend):
    """Run firmware tests via PlatformIO's ``pio test``."""

    def run_tests(self, request: TestRequest) -> TestOutcome:
        project_dir = request.project_dir or _DEFAULT_PROJECT
        envs_run: list[str] = []
        combined_output: list[str] = []

        envs = request.environments or [TestEnvironment.NATIVE]

        for test_env in envs:
            pio_env = _ENV_MAP.get(test_env, str(test_env))
            envs_run.append(pio_env)

            cmd = _find_pio() + ["test", "-e", pio_env]
            if request.filter_pattern:
                cmd.extend(["-f", request.filter_pattern])
            if request.verbose:
                cmd.append("-v")

            print(f"[pio-test] Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=not request.verbose,
                text=True,
            )

            if not request.verbose:
                combined_output.append(result.stdout or "")
                if result.stderr:
                    combined_output.append(result.stderr)

            if result.returncode != 0:
                return TestOutcome(
                    success=False,
                    return_code=result.returncode,
                    output="\n".join(combined_output),
                    error=result.stderr or "",
                    environments_run=envs_run,
                )

        return TestOutcome(
            success=True,
            return_code=0,
            output="\n".join(combined_output),
            environments_run=envs_run,
        )
