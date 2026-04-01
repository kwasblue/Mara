# services/build/backends/cmake/test_backend.py
"""CMake/CTest implementation of the TestBackend interface.

Uses ctest for running tests, or pytest for host-side tests.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..interfaces import TestBackend
from ..models import TestEnvironment, TestRequest, TestOutcome


# Default firmware project path
_DEFAULT_PROJECT = Path(__file__).resolve().parents[6] / "firmware" / "mcu"


def _find_ctest() -> str | None:
    """Find ctest executable."""
    return shutil.which("ctest")


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


class CMakeTestBackend(TestBackend):
    """Run tests via CTest or ESP-IDF's pytest integration."""

    def __init__(self, build_dir: str = "build"):
        self.build_dir = build_dir

    def run_tests(self, request: TestRequest) -> TestOutcome:
        project_dir = request.project_dir or _DEFAULT_PROJECT
        build_path = project_dir / self.build_dir
        envs_run: list[str] = []
        combined_output: list[str] = []

        envs = request.environments or [TestEnvironment.NATIVE]

        for test_env in envs:
            if test_env == TestEnvironment.NATIVE:
                outcome = self._run_native_tests(request, project_dir, build_path)
            else:
                outcome = self._run_device_tests(request, project_dir)

            envs_run.append(str(test_env))
            combined_output.append(outcome.output)

            if not outcome.success:
                return TestOutcome(
                    success=False,
                    return_code=outcome.return_code,
                    output="\n".join(combined_output),
                    error=outcome.error,
                    environments_run=envs_run,
                )

        return TestOutcome(
            success=True,
            return_code=0,
            output="\n".join(combined_output),
            environments_run=envs_run,
        )

    def _run_native_tests(self, request: TestRequest, project_dir: Path, build_path: Path) -> TestOutcome:
        """Run native/host tests using CTest."""
        ctest = _find_ctest()
        if not ctest:
            return TestOutcome(
                success=False,
                return_code=1,
                error="ctest not found",
            )

        # Make sure tests are built
        if not build_path.exists():
            return TestOutcome(
                success=False,
                return_code=1,
                error=f"Build directory {build_path} does not exist. Run build first.",
            )

        cmd = [ctest, "--test-dir", str(build_path)]

        if request.filter_pattern:
            cmd.extend(["-R", request.filter_pattern])

        if request.verbose:
            cmd.extend(["--output-on-failure", "-V"])
        else:
            cmd.append("--output-on-failure")

        print(f"[cmake-test] Running: {' '.join(cmd)}")
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

        return TestOutcome(
            success=result.returncode == 0,
            return_code=result.returncode,
            output=output,
            error=error,
        )

    def _run_device_tests(self, request: TestRequest, project_dir: Path) -> TestOutcome:
        """Run on-device tests using ESP-IDF's pytest or Unity."""
        # Check if this is an ESP-IDF project with pytest
        if _is_espidf_project(project_dir):
            idf_py = _find_idf_py()
            if idf_py:
                # ESP-IDF uses pytest for device tests
                cmd = [idf_py, "-T", "unit_test"]

                print(f"[cmake-test] Running: {' '.join(cmd)}")
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

                return TestOutcome(
                    success=result.returncode == 0,
                    return_code=result.returncode,
                    output=output,
                    error=error,
                )

        # Fallback: device tests not supported for generic CMake
        return TestOutcome(
            success=False,
            return_code=1,
            error="Device tests not supported for non-ESP-IDF CMake projects. "
                  "Consider using native tests with mocked hardware.",
        )
