# services/build/backends/models.py
"""MARA-owned vocabulary for build, flash, and test operations.

These dataclasses define what MARA asks for and what it gets back.
No backend-specific concepts leak into these models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

@dataclass
class BuildRequest:
    """What MARA needs to compile firmware."""
    environment: str = "esp32_usb"
    features: dict[str, bool] = field(default_factory=dict)
    verbose: bool = False
    project_dir: Optional[Path] = None


@dataclass
class BuildOutcome:
    """What MARA gets back after a compile."""
    success: bool
    return_code: int
    output: str = ""
    error: str = ""
    firmware_size: Optional[int] = None
    ram_usage: Optional[int] = None


# ---------------------------------------------------------------------------
# Flash
# ---------------------------------------------------------------------------

@dataclass
class FlashRequest:
    """What MARA needs to flash a device."""
    environment: str = "esp32_usb"
    port: Optional[str] = None
    baud: int = 115200
    verbose: bool = False
    project_dir: Optional[Path] = None
    direct: bool = False  # Skip build tool upload, use direct flashing (e.g., esptool)


@dataclass
class FlashOutcome:
    """What MARA gets back after a flash."""
    success: bool
    return_code: int
    output: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

class TestEnvironment(str, Enum):
    """Standard test environments MARA understands."""

    __test__ = False  # Prevent pytest collection

    NATIVE = "native"          # Desktop / host-compiled unit tests
    DEVICE = "device"          # On-target tests via serial

    def __str__(self) -> str:
        return self.value


@dataclass
class TestRequest:
    """What MARA needs to run firmware tests."""

    __test__ = False  # Prevent pytest collection

    environments: list[TestEnvironment] = field(
        default_factory=lambda: [TestEnvironment.NATIVE],
    )
    filter_pattern: Optional[str] = None
    verbose: bool = False
    project_dir: Optional[Path] = None


@dataclass
class TestOutcome:
    """What MARA gets back after running tests."""

    __test__ = False  # Prevent pytest collection

    success: bool
    return_code: int
    output: str = ""
    error: str = ""
    environments_run: list[str] = field(default_factory=list)
