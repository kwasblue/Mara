# mara_host/services/build/firmware_service.py
"""
Firmware build service.

Provides a clean interface for building, uploading, and testing
ESP32 firmware using PlatformIO.
"""

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

from mara_host.tools.build_firmware import (
    MCU_PROJECT,
    ENVIRONMENTS,
    FEATURES,
    PRESETS,
    parse_features,
    features_to_flags,
    run_pio,
)


class BuildStage(Enum):
    """Build progress stages."""
    STARTING = "starting"
    COMPILING = "compiling"
    LINKING = "linking"
    BUILDING_BINARY = "building_binary"
    UPLOADING = "uploading"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    return_code: int
    output: str = ""
    error: str = ""
    firmware_size: Optional[int] = None
    ram_usage: Optional[int] = None


@dataclass
class FirmwareSize:
    """Firmware size information."""
    flash_used: int
    flash_total: int
    ram_used: int
    ram_total: int

    @property
    def flash_percent(self) -> float:
        return (self.flash_used / self.flash_total) * 100 if self.flash_total else 0

    @property
    def ram_percent(self) -> float:
        return (self.ram_used / self.ram_total) * 100 if self.ram_total else 0


@dataclass
class BuildConfig:
    """Configuration for a firmware build."""
    environment: str = "esp32_motors"
    features: dict[str, bool] = field(default_factory=dict)
    verbose: bool = False
    generate_first: bool = False
    project_path: Path = MCU_PROJECT


class FirmwareBuildService:
    """
    Service for building and managing ESP32 firmware.

    Example:
        service = FirmwareBuildService()

        # Build with preset
        result = await service.build_preset("motors")

        # Build with custom features
        result = await service.build(
            environment="esp32_base",
            features=["wifi", "servo", "telemetry"]
        )

        # Upload to device
        result = await service.upload()
    """

    def __init__(self, project_path: Path = MCU_PROJECT):
        """
        Initialize firmware build service.

        Args:
            project_path: Path to PlatformIO project
        """
        self.project_path = project_path
        self._last_environment: Optional[str] = None
        self._progress_callback: Optional[Callable[[BuildStage, str], None]] = None

    # -------------------------------------------------------------------------
    # Build operations
    # -------------------------------------------------------------------------

    def build(
        self,
        environment: str = "esp32_motors",
        features: Optional[list[str]] = None,
        no_features: Optional[list[str]] = None,
        verbose: bool = False,
        generate_first: bool = False,
    ) -> BuildResult:
        """
        Build the firmware.

        Args:
            environment: PlatformIO environment name
            features: Features to enable (e.g., ["wifi", "servo"])
            no_features: Features to explicitly disable
            verbose: Show verbose output
            generate_first: Run code generators before building

        Returns:
            BuildResult with success status and output
        """
        if environment not in ENVIRONMENTS:
            return BuildResult(
                success=False,
                return_code=1,
                error=f"Unknown environment: {environment}. Available: {', '.join(sorted(ENVIRONMENTS))}"
            )

        self._last_environment = environment

        # Run generators if requested
        if generate_first:
            self._notify_progress(BuildStage.STARTING, "Running code generators...")
            gen_result = self._run_generators()
            if not gen_result.success:
                return gen_result

        # Parse features
        features_str = ",".join(features) if features else None
        no_features_str = ",".join(no_features) if no_features else None
        feature_dict = parse_features(features_str, no_features_str)
        build_flags = features_to_flags(feature_dict)

        # Build args
        args = ["run", "-e", environment]
        if build_flags:
            args.extend(["--build-flag", " ".join(build_flags)])

        self._notify_progress(BuildStage.COMPILING, f"Building {environment}...")

        # Run build
        result = run_pio(args, verbose=verbose, capture=True)

        if result == 0:
            self._notify_progress(BuildStage.COMPLETE, "Build successful")
            return BuildResult(success=True, return_code=0)
        else:
            self._notify_progress(BuildStage.FAILED, "Build failed")
            return BuildResult(success=False, return_code=result)

    def build_preset(
        self,
        preset: str,
        environment: str = "esp32_base",
        verbose: bool = False,
        generate_first: bool = False,
    ) -> BuildResult:
        """
        Build using a feature preset.

        Args:
            preset: Preset name ("minimal", "motors", "sensors", "control", "full")
            environment: Base environment to use
            verbose: Show verbose output
            generate_first: Run generators first

        Returns:
            BuildResult
        """
        if preset not in PRESETS:
            return BuildResult(
                success=False,
                return_code=1,
                error=f"Unknown preset: {preset}. Available: {', '.join(PRESETS.keys())}"
            )

        features = PRESETS[preset]
        return self.build(
            environment=environment,
            features=features,
            verbose=verbose,
            generate_first=generate_first,
        )

    def upload(
        self,
        environment: Optional[str] = None,
        verbose: bool = False,
    ) -> BuildResult:
        """
        Upload firmware to the device.

        Args:
            environment: Environment to upload (uses last built if not specified)
            verbose: Show verbose output

        Returns:
            BuildResult
        """
        env = environment or self._last_environment
        if not env:
            return BuildResult(
                success=False,
                return_code=1,
                error="No environment specified and no previous build"
            )

        self._notify_progress(BuildStage.UPLOADING, f"Uploading to device...")

        args = ["run", "-e", env, "-t", "upload"]
        result = run_pio(args, verbose=verbose, capture=True)

        if result == 0:
            self._notify_progress(BuildStage.COMPLETE, "Upload successful")
            return BuildResult(success=True, return_code=0)
        else:
            self._notify_progress(BuildStage.FAILED, "Upload failed")
            return BuildResult(success=False, return_code=result)

    def clean(self, environment: Optional[str] = None) -> BuildResult:
        """
        Clean build artifacts.

        Args:
            environment: Environment to clean (all if not specified)

        Returns:
            BuildResult
        """
        args = ["run", "-t", "clean"]
        if environment:
            args.extend(["-e", environment])

        result = run_pio(args, capture=True)

        return BuildResult(
            success=result == 0,
            return_code=result
        )

    def test(
        self,
        native: bool = True,
        device: bool = False,
        verbose: bool = False,
    ) -> BuildResult:
        """
        Run firmware tests.

        Args:
            native: Run native (desktop) tests
            device: Run on-device tests
            verbose: Show verbose output

        Returns:
            BuildResult
        """
        args = ["test"]

        if native and not device:
            args.extend(["-e", "native"])
        elif device and not native:
            args.extend(["-e", "esp32_test"])
        # If both, run all test environments

        if verbose:
            args.append("-v")

        result = run_pio(args, verbose=verbose, capture=True)

        return BuildResult(
            success=result == 0,
            return_code=result
        )

    # -------------------------------------------------------------------------
    # Size analysis
    # -------------------------------------------------------------------------

    def get_size(self, environment: Optional[str] = None) -> Optional[FirmwareSize]:
        """
        Get firmware size information.

        Args:
            environment: Environment to check (uses last built if not specified)

        Returns:
            FirmwareSize or None if unavailable
        """
        env = environment or self._last_environment
        if not env:
            return None

        args = ["run", "-e", env, "-t", "size"]
        try:
            result = subprocess.run(
                ["pio"] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
            )

            # Parse size output
            return self._parse_size_output(result.stdout)
        except Exception:
            return None

    def _parse_size_output(self, output: str) -> Optional[FirmwareSize]:
        """Parse PlatformIO size output."""
        # Look for lines like:
        # RAM:   [==        ]  17.3% (used 56620 bytes from 327680 bytes)
        # Flash: [=====     ]  45.9% (used 872369 bytes from 1900544 bytes)

        import re

        ram_match = re.search(
            r"RAM:.*used (\d+) bytes from (\d+) bytes",
            output
        )
        flash_match = re.search(
            r"Flash:.*used (\d+) bytes from (\d+) bytes",
            output
        )

        if ram_match and flash_match:
            return FirmwareSize(
                flash_used=int(flash_match.group(1)),
                flash_total=int(flash_match.group(2)),
                ram_used=int(ram_match.group(1)),
                ram_total=int(ram_match.group(2)),
            )

        return None

    # -------------------------------------------------------------------------
    # Information
    # -------------------------------------------------------------------------

    @staticmethod
    def get_available_environments() -> set[str]:
        """Get available PlatformIO environments."""
        return ENVIRONMENTS.copy()

    @staticmethod
    def get_available_features() -> dict[str, str]:
        """Get available features and their C macros."""
        return FEATURES.copy()

    @staticmethod
    def get_presets() -> dict[str, list[str]]:
        """Get feature presets."""
        return {k: list(v) for k, v in PRESETS.items()}

    # -------------------------------------------------------------------------
    # Progress tracking
    # -------------------------------------------------------------------------

    def set_progress_callback(
        self,
        callback: Callable[[BuildStage, str], None]
    ) -> None:
        """Set callback for build progress updates."""
        self._progress_callback = callback

    def _notify_progress(self, stage: BuildStage, message: str) -> None:
        """Notify progress callback if set."""
        if self._progress_callback:
            self._progress_callback(stage, message)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _run_generators(self) -> BuildResult:
        """Run code generators."""
        try:
            from mara_host.tools.generate_all import main as generate_main
            generate_main()
            return BuildResult(success=True, return_code=0)
        except Exception as e:
            return BuildResult(
                success=False,
                return_code=1,
                error=str(e)
            )
