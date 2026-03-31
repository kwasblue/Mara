# services/build/backends/interfaces.py
"""Abstract base classes for build, flash, and test backends.

Each ABC defines exactly one capability.  A concrete adapter (PlatformIO today,
CMake / ESP-IDF / custom tomorrow) implements one or more of these.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    BuildRequest, BuildOutcome,
    FlashRequest, FlashOutcome,
    TestRequest, TestOutcome,
)


class BuildBackend(ABC):
    """Compile firmware from source."""

    @abstractmethod
    def build(self, request: BuildRequest) -> BuildOutcome:
        """Compile firmware according to *request*."""

    @abstractmethod
    def clean(self, environment: str | None = None) -> BuildOutcome:
        """Remove build artefacts."""

    @abstractmethod
    def get_version(self) -> str | None:
        """Return the backend's version string, or ``None`` if unavailable."""


class FlashBackend(ABC):
    """Upload compiled firmware to a device."""

    @abstractmethod
    def flash(self, request: FlashRequest) -> FlashOutcome:
        """Flash firmware according to *request*."""

    @abstractmethod
    def detect_devices(self) -> list[str]:
        """Return serial ports with connected devices."""


class TestBackend(ABC):
    """Run firmware unit / integration tests."""

    @abstractmethod
    def run_tests(self, request: TestRequest) -> TestOutcome:
        """Execute tests according to *request* and return the outcome."""
