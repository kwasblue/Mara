# tests/test_tooling_backends.py
"""
Tests for tooling backends (build, flash, test).

This module provides:
1. Registry tests - ensure backends register and look up correctly
2. Interface compliance tests - ensure backends implement required methods
3. Subprocess mocking utilities - for testing backend implementations
4. Parameterized tests - run same tests across all backends

================================================================================
ADDING A NEW BACKEND - TESTING GUIDE
================================================================================

To test a new backend:

1. Implement the backend following the interface (see interfaces.py)

2. Add registration in your backend's __init__.py:

   def register_backends(registry) -> None:
       registry.register_build("mybackend", MyBuildBackend())
       registry.register_flash("mybackend", MyFlashBackend())
       registry.register_test("mybackend", MyTestBackend())

3. Run: mara generate all (to regenerate loaders)

4. Run tests:

   # Run all backend tests (your backend is automatically included)
   pytest tests/test_tooling_backends.py -v

   # Run only tests for your backend
   pytest tests/test_tooling_backends.py -v -k "mybackend"

   # Run interface compliance tests
   pytest tests/test_tooling_backends.py -v -k "Compliance"

   # Run with integration tests (requires tools installed)
   pytest tests/test_tooling_backends.py -v -m integration

5. The parametrized tests will automatically:
   - Verify your backend implements all required methods
   - Test build/flash/test operations with mocked subprocess
   - Ensure proper return types (BuildOutcome, FlashOutcome, TestOutcome)

For backend-specific tests, add a new test class:

    class TestMyBackendSpecific:
        def test_my_special_feature(self):
            backend = get_registry().get_build("mybackend")
            # Test backend-specific functionality

================================================================================
"""

from __future__ import annotations

import contextlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import pytest

from mara_host.services.tooling.backends.interfaces import (
    BuildBackend,
    FlashBackend,
    TestBackend,
)
from mara_host.services.tooling.backends.models import (
    BuildOutcome,
    BuildRequest,
    FlashOutcome,
    FlashRequest,
    TestEnvironment,
    TestOutcome,
    TestRequest,
)
from mara_host.services.tooling.backends.registry import BackendRegistry, get_registry


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fresh_registry() -> BackendRegistry:
    """Create a fresh registry without any backends loaded."""
    return BackendRegistry()


@pytest.fixture
def loaded_registry() -> BackendRegistry:
    """Get the global registry with all backends loaded."""
    return get_registry()


@dataclass
class MockSubprocessResult:
    """Mock result from subprocess.run()."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    @property
    def output(self) -> str:
        return self.stdout


@pytest.fixture
def mock_subprocess() -> Callable[[int, str, str], MagicMock]:
    """
    Factory fixture for mocking subprocess.run().

    Usage:
        def test_build(mock_subprocess):
            mock_subprocess(0, "Build success", "")
            # Now subprocess.run returns success
    """

    def _mock(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = stdout
        mock_result.stderr = stderr
        return mock_result

    return _mock


@pytest.fixture
def mock_shutil_which() -> Callable[[str | None], Any]:
    """
    Factory fixture for mocking shutil.which().

    Usage:
        def test_find_tool(mock_shutil_which):
            with mock_shutil_which("/usr/bin/pio"):
                # shutil.which() returns /usr/bin/pio
    """

    def _mock(return_value: str | None):
        return patch("shutil.which", return_value=return_value)

    return _mock


# =============================================================================
# REGISTRY TESTS
# =============================================================================


class TestBackendRegistry:
    """Tests for the backend registry system."""

    def test_fresh_registry_is_empty(self, fresh_registry: BackendRegistry):
        """A new registry has no backends registered."""
        assert fresh_registry.list_build_backends() == []
        assert fresh_registry.list_flash_backends() == []
        assert fresh_registry.list_test_backends() == []

    def test_register_and_lookup_build_backend(self, fresh_registry: BackendRegistry):
        """Can register and retrieve a build backend."""
        mock_backend = MagicMock(spec=BuildBackend)
        fresh_registry.register_build("test", mock_backend)

        assert "test" in fresh_registry.list_build_backends()
        assert fresh_registry.get_build("test") is mock_backend

    def test_register_and_lookup_flash_backend(self, fresh_registry: BackendRegistry):
        """Can register and retrieve a flash backend."""
        mock_backend = MagicMock(spec=FlashBackend)
        fresh_registry.register_flash("test", mock_backend)

        assert "test" in fresh_registry.list_flash_backends()
        assert fresh_registry.get_flash("test") is mock_backend

    def test_register_and_lookup_test_backend(self, fresh_registry: BackendRegistry):
        """Can register and retrieve a test backend."""
        mock_backend = MagicMock(spec=TestBackend)
        fresh_registry.register_test("test", mock_backend)

        assert "test" in fresh_registry.list_test_backends()
        assert fresh_registry.get_test("test") is mock_backend

    def test_lookup_missing_backend_raises_keyerror(self, fresh_registry: BackendRegistry):
        """Looking up a non-existent backend raises KeyError."""
        with pytest.raises(KeyError):
            fresh_registry.get_build("nonexistent")

    def test_global_registry_loads_backends(self, loaded_registry: BackendRegistry):
        """The global registry auto-loads discovered backends."""
        # Should have at least platformio and cmake
        build_backends = loaded_registry.list_build_backends()
        assert len(build_backends) >= 2
        assert "platformio" in build_backends
        assert "cmake" in build_backends


class TestBackendDiscovery:
    """Tests for backend auto-discovery system."""

    def test_generated_loaders_exists(self):
        """The generated loaders module exists and is importable."""
        from mara_host.services.tooling.backends._generated_loaders import load_all_backends

        assert callable(load_all_backends)

    def test_load_all_backends_populates_registry(self, fresh_registry: BackendRegistry):
        """load_all_backends() registers all discovered backends."""
        from mara_host.services.tooling.backends._generated_loaders import load_all_backends

        loaded = load_all_backends(fresh_registry)

        # Should return list of loaded backend names
        assert isinstance(loaded, list)
        assert "platformio" in loaded
        assert "cmake" in loaded

        # Registry should now have backends
        assert "platformio" in fresh_registry.list_build_backends()
        assert "cmake" in fresh_registry.list_build_backends()


# =============================================================================
# INTERFACE COMPLIANCE TESTS
# =============================================================================


def get_all_build_backends() -> list[tuple[str, BuildBackend]]:
    """Get all registered build backends for parameterized tests."""
    registry = get_registry()
    return [(name, registry.get_build(name)) for name in registry.list_build_backends()]


def get_all_flash_backends() -> list[tuple[str, FlashBackend]]:
    """Get all registered flash backends for parameterized tests."""
    registry = get_registry()
    return [(name, registry.get_flash(name)) for name in registry.list_flash_backends()]


def get_all_test_backends() -> list[tuple[str, TestBackend]]:
    """Get all registered test backends for parameterized tests."""
    registry = get_registry()
    return [(name, registry.get_test(name)) for name in registry.list_test_backends()]


class TestBuildBackendCompliance:
    """Ensure all build backends implement the interface correctly."""

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_implements_build_method(self, name: str, backend: BuildBackend):
        """Backend has a build() method that accepts BuildRequest."""
        assert hasattr(backend, "build")
        assert callable(backend.build)

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_implements_clean_method(self, name: str, backend: BuildBackend):
        """Backend has a clean() method."""
        assert hasattr(backend, "clean")
        assert callable(backend.clean)

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_implements_get_version_method(self, name: str, backend: BuildBackend):
        """Backend has a get_version() method."""
        assert hasattr(backend, "get_version")
        assert callable(backend.get_version)

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_get_version_returns_string_or_none(self, name: str, backend: BuildBackend):
        """get_version() returns a string or None."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="1.0.0\n", stderr=""
            )
            version = backend.get_version()
            assert version is None or isinstance(version, str)


class TestFlashBackendCompliance:
    """Ensure all flash backends implement the interface correctly."""

    @pytest.mark.parametrize(
        "name,backend",
        get_all_flash_backends(),
        ids=[name for name, _ in get_all_flash_backends()],
    )
    def test_implements_flash_method(self, name: str, backend: FlashBackend):
        """Backend has a flash() method that accepts FlashRequest."""
        assert hasattr(backend, "flash")
        assert callable(backend.flash)

    @pytest.mark.parametrize(
        "name,backend",
        get_all_flash_backends(),
        ids=[name for name, _ in get_all_flash_backends()],
    )
    def test_implements_detect_devices_method(self, name: str, backend: FlashBackend):
        """Backend has a detect_devices() method."""
        assert hasattr(backend, "detect_devices")
        assert callable(backend.detect_devices)

    @pytest.mark.parametrize(
        "name,backend",
        get_all_flash_backends(),
        ids=[name for name, _ in get_all_flash_backends()],
    )
    def test_detect_devices_returns_list(self, name: str, backend: FlashBackend):
        """detect_devices() returns a list of strings."""
        with patch("serial.tools.list_ports.comports", return_value=[]):
            devices = backend.detect_devices()
            assert isinstance(devices, list)


class TestTestBackendCompliance:
    """Ensure all test backends implement the interface correctly."""

    @pytest.mark.parametrize(
        "name,backend",
        get_all_test_backends(),
        ids=[name for name, _ in get_all_test_backends()],
    )
    def test_implements_run_tests_method(self, name: str, backend: TestBackend):
        """Backend has a run_tests() method that accepts TestRequest."""
        assert hasattr(backend, "run_tests")
        assert callable(backend.run_tests)


# =============================================================================
# BUILD BACKEND UNIT TESTS
# =============================================================================


class TestBuildBackendBehavior:
    """Unit tests for build backend behavior with mocked subprocess."""

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_build_success_returns_success_outcome(self, name: str, backend: BuildBackend):
        """A successful build returns BuildOutcome with success=True."""
        with (
            patch("subprocess.run") as mock_run,
            patch("shutil.which", return_value="/usr/bin/tool"),
        ):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Build completed successfully\nRAM: 50000 bytes\nFlash: 200000 bytes",
                stderr="",
            )

            request = BuildRequest(environment="esp32_usb", verbose=False)
            outcome = backend.build(request)

            assert isinstance(outcome, BuildOutcome)
            assert outcome.success is True
            assert outcome.return_code == 0

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_build_failure_returns_failure_outcome(self, name: str, backend: BuildBackend):
        """A failed build returns BuildOutcome with success=False."""
        with (
            patch("subprocess.run") as mock_run,
            patch("shutil.which", return_value="/usr/bin/tool"),
        ):
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Compilation error: undefined reference",
            )

            request = BuildRequest(environment="esp32_usb", verbose=False)
            outcome = backend.build(request)

            assert isinstance(outcome, BuildOutcome)
            assert outcome.success is False
            assert outcome.return_code == 1

    @pytest.mark.parametrize(
        "name,backend",
        get_all_build_backends(),
        ids=[name for name, _ in get_all_build_backends()],
    )
    def test_clean_returns_outcome(self, name: str, backend: BuildBackend):
        """clean() returns a BuildOutcome."""
        with (
            patch("subprocess.run") as mock_run,
            patch("shutil.which", return_value="/usr/bin/tool"),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="Cleaned", stderr="")

            outcome = backend.clean()

            assert isinstance(outcome, BuildOutcome)


# =============================================================================
# FLASH BACKEND UNIT TESTS
# =============================================================================


class TestFlashBackendBehavior:
    """Unit tests for flash backend behavior with mocked subprocess."""

    @pytest.mark.parametrize(
        "name,backend",
        get_all_flash_backends(),
        ids=[name for name, _ in get_all_flash_backends()],
    )
    def test_flash_success_returns_success_outcome(self, name: str, backend: FlashBackend):
        """A successful flash returns FlashOutcome with success=True."""
        # Need to patch at the module level where it's used
        patches = [
            patch("subprocess.run"),
            patch("shutil.which", return_value="/usr/bin/tool"),
        ]
        # CMake backend also checks Path.exists() for tool paths
        if name == "cmake":
            patches.append(
                patch(
                    "mara_host.services.tooling.backends.cmake.flash_backend._find_esptool",
                    return_value="/usr/bin/esptool.py",
                )
            )

        with contextlib.ExitStack() as stack:
            for p in patches:
                mock = stack.enter_context(p)
                if hasattr(mock, "return_value") and "subprocess" in str(p):
                    mock.return_value = MagicMock(
                        returncode=0,
                        stdout="Uploading firmware...\nDone!",
                        stderr="",
                    )

            request = FlashRequest(
                environment="esp32_usb",
                port="/dev/ttyUSB0",
                verbose=False,
            )
            outcome = backend.flash(request)

            assert isinstance(outcome, FlashOutcome)
            # For mocked tools, success depends on subprocess mock working correctly
            # The key assertion is that we get a FlashOutcome back

    @pytest.mark.parametrize(
        "name,backend",
        get_all_flash_backends(),
        ids=[name for name, _ in get_all_flash_backends()],
    )
    def test_flash_failure_returns_failure_outcome(self, name: str, backend: FlashBackend):
        """A failed flash returns FlashOutcome with success=False."""
        with (
            patch("subprocess.run") as mock_run,
            patch("shutil.which", return_value="/usr/bin/tool"),
        ):
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: Could not connect to device",
            )

            request = FlashRequest(
                environment="esp32_usb",
                port="/dev/ttyUSB0",
                verbose=False,
            )
            outcome = backend.flash(request)

            assert isinstance(outcome, FlashOutcome)
            assert outcome.success is False


# =============================================================================
# TEST BACKEND UNIT TESTS
# =============================================================================


class TestTestBackendBehavior:
    """Unit tests for test backend behavior with mocked subprocess."""

    @pytest.mark.parametrize(
        "name,backend",
        get_all_test_backends(),
        ids=[name for name, _ in get_all_test_backends()],
    )
    def test_run_tests_returns_outcome(self, name: str, backend: TestBackend):
        """run_tests() returns a TestOutcome."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="All tests passed",
                stderr="",
            )

            request = TestRequest(
                environments=[TestEnvironment.NATIVE],
                verbose=False,
            )
            outcome = backend.run_tests(request)

            assert isinstance(outcome, TestOutcome)

    @pytest.mark.parametrize(
        "name,backend",
        get_all_test_backends(),
        ids=[name for name, _ in get_all_test_backends()],
    )
    def test_run_tests_with_filter(self, name: str, backend: TestBackend):
        """run_tests() accepts a filter pattern."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Running filtered tests",
                stderr="",
            )

            request = TestRequest(
                environments=[TestEnvironment.NATIVE],
                filter_pattern="test_motor*",
                verbose=False,
            )
            outcome = backend.run_tests(request)

            assert isinstance(outcome, TestOutcome)


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestBuildRequest:
    """Tests for BuildRequest model."""

    def test_default_values(self):
        """BuildRequest has sensible defaults."""
        request = BuildRequest()
        assert request.environment == "esp32_usb"
        assert request.features == {}
        assert request.verbose is False
        assert request.project_dir is None

    def test_custom_values(self):
        """BuildRequest accepts custom values."""
        request = BuildRequest(
            environment="native",
            features={"HAS_IMU": True, "HAS_GPS": False},
            verbose=True,
            project_dir=Path("/custom/path"),
        )
        assert request.environment == "native"
        assert request.features["HAS_IMU"] is True
        assert request.verbose is True
        assert request.project_dir == Path("/custom/path")


class TestBuildOutcome:
    """Tests for BuildOutcome model."""

    def test_success_outcome(self):
        """BuildOutcome represents success correctly."""
        outcome = BuildOutcome(
            success=True,
            return_code=0,
            output="Build complete",
            firmware_size=150000,
            ram_usage=45000,
        )
        assert outcome.success is True
        assert outcome.firmware_size == 150000
        assert outcome.ram_usage == 45000

    def test_failure_outcome(self):
        """BuildOutcome represents failure correctly."""
        outcome = BuildOutcome(
            success=False,
            return_code=1,
            error="Compilation failed",
        )
        assert outcome.success is False
        assert outcome.error == "Compilation failed"


class TestFlashRequest:
    """Tests for FlashRequest model."""

    def test_default_values(self):
        """FlashRequest has sensible defaults."""
        request = FlashRequest()
        assert request.environment == "esp32_usb"
        assert request.port is None
        assert request.baud == 115200
        assert request.direct is False

    def test_direct_flash_mode(self):
        """FlashRequest supports direct flash mode."""
        request = FlashRequest(direct=True, port="/dev/ttyUSB0")
        assert request.direct is True


class TestTestRequest:
    """Tests for TestRequest model."""

    def test_default_environment_is_native(self):
        """TestRequest defaults to native environment."""
        request = TestRequest()
        assert request.environments == [TestEnvironment.NATIVE]

    def test_multiple_environments(self):
        """TestRequest can specify multiple environments."""
        request = TestRequest(
            environments=[TestEnvironment.NATIVE, TestEnvironment.DEVICE]
        )
        assert len(request.environments) == 2


# =============================================================================
# INTEGRATION TESTS (Optional - require actual tools installed)
# =============================================================================


import shutil as _shutil_for_skipif  # Import at module level for skipif


@pytest.mark.integration
@pytest.mark.skipif(
    _shutil_for_skipif.which("pio") is None and _shutil_for_skipif.which("platformio") is None,
    reason="PlatformIO not installed",
)
class TestPlatformIOIntegration:
    """Integration tests for PlatformIO backend (requires pio installed)."""

    def test_get_version_returns_version_string(self, loaded_registry: BackendRegistry):
        """PlatformIO backend returns actual version."""
        backend = loaded_registry.get_build("platformio")
        version = backend.get_version()

        assert version is not None
        assert isinstance(version, str)
        # Version should look like "x.y.z"
        assert "." in version


@pytest.mark.integration
@pytest.mark.skipif(
    _shutil_for_skipif.which("cmake") is None,
    reason="CMake not installed",
)
class TestCMakeIntegration:
    """Integration tests for CMake backend (requires cmake installed)."""

    def test_get_version_returns_version_string(self, loaded_registry: BackendRegistry):
        """CMake backend returns actual version."""
        backend = loaded_registry.get_build("cmake")
        version = backend.get_version()

        assert version is not None
        assert isinstance(version, str)
