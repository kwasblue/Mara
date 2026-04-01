# services/tooling/tooling_service.py
"""Unified tooling service for build, flash, and test operations.

This is the MARA-owned service layer that coordinates all tooling operations.
It provides a clean interface for CLI/GUI and delegates to pluggable backends.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .backends import (
    get_registry,
    BuildRequest,
    BuildOutcome,
    FlashRequest,
    FlashOutcome,
    TestRequest,
    TestOutcome,
    TestEnvironment,
)
from .device_service import DeviceService, DeviceInfo


@dataclass
class ToolingConfig:
    """Configuration for tooling operations."""
    backend: str = "platformio"
    environment: str = "esp32_usb"
    project_dir: Optional[Path] = None
    verbose: bool = False


class ToolingService:
    """Unified service for all tooling operations.

    This is the main entry point for build/flash/test operations.
    It coordinates between device detection and build backends.

    Example:
        tooling = ToolingService()
        tooling.set_backend("cmake")

        # Build
        result = tooling.build(environment="esp32_usb", features={"HAS_WIFI": True})

        # Auto-detect and flash
        result = tooling.flash_auto()

        # Or flash to specific port
        result = tooling.flash(port="/dev/ttyUSB0")

        # Run tests
        result = tooling.test(native=True)
    """

    def __init__(self, config: Optional[ToolingConfig] = None):
        self._config = config or ToolingConfig()
        self._device_service = DeviceService()
        self._registry = get_registry()

    @property
    def device_service(self) -> DeviceService:
        """Access device service for device operations."""
        return self._device_service

    @property
    def backend(self) -> str:
        """Current backend name."""
        return self._config.backend

    @backend.setter
    def backend(self, name: str) -> None:
        """Set the backend to use."""
        self._config.backend = name

    def set_backend(self, name: str) -> None:
        """Set the backend to use for operations."""
        self._config.backend = name

    def list_backends(self) -> dict[str, list[str]]:
        """List available backends by type."""
        return {
            "build": self._registry.list_build_backends(),
            "flash": self._registry.list_flash_backends(),
            "test": self._registry.list_test_backends(),
        }

    # =========================================================================
    # Build Operations
    # =========================================================================

    def build(
        self,
        environment: Optional[str] = None,
        features: Optional[dict[str, bool]] = None,
        verbose: Optional[bool] = None,
        project_dir: Optional[Path] = None,
    ) -> BuildOutcome:
        """Build firmware.

        Args:
            environment: Build environment/target (default: from config)
            features: Feature flags to enable/disable
            verbose: Verbose output (default: from config)
            project_dir: Project directory (default: from config)

        Returns:
            BuildOutcome with success status and details
        """
        request = BuildRequest(
            environment=environment or self._config.environment,
            features=features or {},
            verbose=verbose if verbose is not None else self._config.verbose,
            project_dir=project_dir or self._config.project_dir,
        )

        backend = self._registry.get_build(self._config.backend)
        return backend.build(request)

    def clean(self, environment: Optional[str] = None) -> BuildOutcome:
        """Clean build artifacts.

        Args:
            environment: Environment to clean (None = all)

        Returns:
            BuildOutcome with success status
        """
        backend = self._registry.get_build(self._config.backend)
        return backend.clean(environment)

    def get_build_version(self) -> Optional[str]:
        """Get the build backend version string."""
        backend = self._registry.get_build(self._config.backend)
        return backend.get_version()

    # =========================================================================
    # Flash Operations
    # =========================================================================

    def flash(
        self,
        port: str,
        environment: Optional[str] = None,
        baud: int = 115200,
        direct: bool = False,
        verbose: Optional[bool] = None,
        project_dir: Optional[Path] = None,
    ) -> FlashOutcome:
        """Flash firmware to a device.

        Args:
            port: Serial port
            environment: Build environment (default: from config)
            baud: Baud rate for flashing
            direct: Use direct flashing (bypass build tool upload)
            verbose: Verbose output
            project_dir: Project directory

        Returns:
            FlashOutcome with success status
        """
        request = FlashRequest(
            environment=environment or self._config.environment,
            port=port,
            baud=baud,
            verbose=verbose if verbose is not None else self._config.verbose,
            project_dir=project_dir or self._config.project_dir,
            direct=direct,
        )

        backend = self._registry.get_flash(self._config.backend)
        return backend.flash(request)

    def flash_auto(
        self,
        environment: Optional[str] = None,
        baud: int = 115200,
        direct: bool = False,
        verbose: Optional[bool] = None,
    ) -> tuple[FlashOutcome, Optional[str]]:
        """Auto-detect device and flash.

        Returns:
            (FlashOutcome, port) - port is None if no device found
        """
        devices = self._device_service.detect_esp32_devices()
        if not devices:
            return FlashOutcome(
                success=False,
                return_code=1,
                error="No devices detected",
            ), None

        # Use first device
        port = devices[0].port
        outcome = self.flash(
            port=port,
            environment=environment,
            baud=baud,
            direct=direct,
            verbose=verbose,
        )
        return outcome, port

    def detect_devices(self) -> list[DeviceInfo]:
        """Detect connected devices."""
        return self._device_service.detect_esp32_devices()

    def erase_flash(self, port: str) -> tuple[bool, str]:
        """Erase device flash memory."""
        return self._device_service.erase_flash(port)

    def get_chip_info(self, port: str) -> Optional[dict]:
        """Get chip information from device."""
        return self._device_service.get_chip_info(port)

    # =========================================================================
    # Test Operations
    # =========================================================================

    def test(
        self,
        native: bool = True,
        device: bool = False,
        filter_pattern: Optional[str] = None,
        verbose: Optional[bool] = None,
        project_dir: Optional[Path] = None,
    ) -> TestOutcome:
        """Run firmware tests.

        Args:
            native: Run native (host) tests
            device: Run on-device tests
            filter_pattern: Filter tests by pattern
            verbose: Verbose output
            project_dir: Project directory

        Returns:
            TestOutcome with success status
        """
        environments = []
        if native:
            environments.append(TestEnvironment.NATIVE)
        if device:
            environments.append(TestEnvironment.DEVICE)
        if not environments:
            environments = [TestEnvironment.NATIVE]

        request = TestRequest(
            environments=environments,
            filter_pattern=filter_pattern,
            verbose=verbose if verbose is not None else self._config.verbose,
            project_dir=project_dir or self._config.project_dir,
        )

        backend = self._registry.get_test(self._config.backend)
        return backend.run_tests(request)
