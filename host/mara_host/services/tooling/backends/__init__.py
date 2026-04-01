# services/tooling/backends/__init__.py
"""Pluggable backend abstraction for build, flash, and test operations.

MARA owns the interfaces; PlatformIO, CMake, and any future tool are adapters.

## Quick Start

    from mara_host.services.tooling.backends import get_registry, BuildRequest

    registry = get_registry()
    build = registry.get_build("platformio")  # or "cmake"
    result = build.build(BuildRequest(environment="esp32dev"))

## Adding New Backends

See README.md in this directory for the full guide.

1. Create directory: backends/mybackend/
2. Implement BuildBackend, FlashBackend, TestBackend
3. Add register_backends() function to __init__.py
4. Run: mara generate tooling
"""

from .interfaces import BuildBackend, FlashBackend, TestBackend
from .models import (
    BuildRequest, BuildOutcome,
    FlashRequest, FlashOutcome,
    TestRequest, TestOutcome,
    TestEnvironment,
)
from .registry import BackendRegistry, get_registry

__all__ = [
    "BuildBackend", "FlashBackend", "TestBackend",
    "BuildRequest", "BuildOutcome",
    "FlashRequest", "FlashOutcome",
    "TestRequest", "TestOutcome",
    "TestEnvironment",
    "BackendRegistry", "get_registry",
]
