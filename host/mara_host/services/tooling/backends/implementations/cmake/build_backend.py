# services/build/backends/cmake/build_backend.py
"""CMake implementation of the BuildBackend interface.

Supports both standalone CMake projects and ESP-IDF CMake projects.
For ESP-IDF, uses idf.py as a wrapper around CMake.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ...interfaces import BuildBackend
from ...models import BuildRequest, BuildOutcome


# Default firmware project path
_DEFAULT_PROJECT = Path(__file__).resolve().parents[7] / "firmware" / "mcu"


def _find_cmake() -> str | None:
    """Find cmake executable."""
    return shutil.which("cmake")


def _find_idf_py() -> str | None:
    """Find idf.py for ESP-IDF projects."""
    return shutil.which("idf.py")


def _is_espidf_project(project_dir: Path) -> bool:
    """Check if this is an ESP-IDF project (has CMakeLists.txt with idf_component_register)."""
    cmakelists = project_dir / "CMakeLists.txt"
    if not cmakelists.exists():
        return False
    try:
        content = cmakelists.read_text()
        return "idf_component_register" in content or "idf_build_process" in content
    except Exception:
        return False


def _features_to_cmake_defs(features: dict[str, bool]) -> list[str]:
    """Convert feature dict to CMake -D definitions."""
    defs = []
    for macro, enabled in features.items():
        defs.extend(["-D", f"{macro}={int(enabled)}"])
    return defs


def _parse_size_output(output: str) -> tuple[int | None, int | None]:
    """Parse firmware and RAM size from build output."""
    firmware_size = None
    ram_usage = None

    # ESP-IDF style: "Total sizes: ... DRAM: 12345 ... Flash code: 67890"
    dram_match = re.search(r"DRAM[^:]*:\s*(\d+)", output)
    flash_match = re.search(r"Flash[^:]*:\s*(\d+)", output)

    if dram_match:
        ram_usage = int(dram_match.group(1))
    if flash_match:
        firmware_size = int(flash_match.group(1))

    # Generic CMake/size output: look for common patterns
    if not firmware_size:
        size_match = re.search(r"text\s+data\s+bss\s+dec.*\n\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", output)
        if size_match:
            text = int(size_match.group(1))
            data = int(size_match.group(2))
            bss = int(size_match.group(3))
            firmware_size = text + data
            ram_usage = data + bss

    return firmware_size, ram_usage


class CMakeBuildBackend(BuildBackend):
    """Compile firmware via CMake or ESP-IDF's idf.py."""

    def __init__(self, build_dir: str = "build"):
        self.build_dir = build_dir

    def build(self, request: BuildRequest) -> BuildOutcome:
        project_dir = request.project_dir or _DEFAULT_PROJECT
        build_path = project_dir / self.build_dir

        # Check if this is an ESP-IDF project
        if _is_espidf_project(project_dir):
            return self._build_espidf(request, project_dir)

        return self._build_cmake(request, project_dir, build_path)

    def _build_espidf(self, request: BuildRequest, project_dir: Path) -> BuildOutcome:
        """Build using idf.py for ESP-IDF projects."""
        idf_py = _find_idf_py()
        if not idf_py:
            return BuildOutcome(
                success=False,
                return_code=1,
                error="idf.py not found. Is ESP-IDF installed and sourced?",
            )

        cmd = [idf_py, "build"]
        if request.verbose:
            cmd.append("-v")

        # Set component config via environment
        env = os.environ.copy()
        if request.features:
            # ESP-IDF uses sdkconfig, but we can pass -D flags
            cmake_defs = _features_to_cmake_defs(request.features)
            if cmake_defs:
                env["EXTRA_COMPONENT_DIRS"] = " ".join(cmake_defs)

        print(f"[cmake-build] Running: {' '.join(cmd)}")

        if request.verbose:
            # Stream output while capturing
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
                print(line, end="")
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

        firmware_size, ram_usage = _parse_size_output(output + error)

        return BuildOutcome(
            success=return_code == 0,
            return_code=return_code,
            output=output,
            error=error,
            firmware_size=firmware_size,
            ram_usage=ram_usage,
        )

    def _build_cmake(self, request: BuildRequest, project_dir: Path, build_path: Path) -> BuildOutcome:
        """Build using standalone CMake."""
        cmake = _find_cmake()
        if not cmake:
            return BuildOutcome(
                success=False,
                return_code=1,
                error="cmake not found",
            )

        # Configure if needed
        if not (build_path / "CMakeCache.txt").exists():
            configure_cmd = [cmake, "-S", str(project_dir), "-B", str(build_path)]

            # Add feature flags as CMake definitions
            if request.features:
                configure_cmd.extend(_features_to_cmake_defs(request.features))

            # Add build type based on environment name
            if "debug" in request.environment.lower():
                configure_cmd.extend(["-DCMAKE_BUILD_TYPE=Debug"])
            else:
                configure_cmd.extend(["-DCMAKE_BUILD_TYPE=Release"])

            print(f"[cmake-build] Configuring: {' '.join(configure_cmd)}")
            config_result = subprocess.run(
                configure_cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if config_result.returncode != 0:
                return BuildOutcome(
                    success=False,
                    return_code=config_result.returncode,
                    output=config_result.stdout or "",
                    error=config_result.stderr or "",
                )

        # Build
        build_cmd = [cmake, "--build", str(build_path)]
        if request.verbose:
            build_cmd.append("--verbose")

        # Parallel build
        build_cmd.extend(["--parallel"])

        print(f"[cmake-build] Building: {' '.join(build_cmd)}")

        if request.verbose:
            # Stream output while capturing
            process = subprocess.Popen(
                build_cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output_lines = []
            for line in process.stdout:
                print(line, end="")
                output_lines.append(line)
            process.wait()
            output = "".join(output_lines)
            error = ""
            return_code = process.returncode
        else:
            result = subprocess.run(
                build_cmd,
                cwd=project_dir,
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
        build_path = project_dir / self.build_dir

        # Check if this is an ESP-IDF project
        if _is_espidf_project(project_dir):
            idf_py = _find_idf_py()
            if idf_py:
                cmd = [idf_py, "fullclean"]
                print(f"[cmake-build] Running: {' '.join(cmd)}")
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

        # Standard CMake clean
        cmake = _find_cmake()
        if not cmake:
            return BuildOutcome(
                success=False,
                return_code=1,
                error="cmake not found",
            )

        if not build_path.exists():
            return BuildOutcome(
                success=True,
                return_code=0,
                output="Build directory does not exist, nothing to clean",
            )

        cmd = [cmake, "--build", str(build_path), "--target", "clean"]
        print(f"[cmake-build] Running: {' '.join(cmd)}")
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
        """Return CMake version string."""
        cmake = _find_cmake()
        if not cmake:
            return None
        try:
            result = subprocess.run([cmake, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                # First line is like "cmake version 3.28.1"
                return result.stdout.split("\n")[0].strip()
        except Exception:
            pass
        return None
