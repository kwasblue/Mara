# services/build/backends/__init__.py
"""Pluggable backend abstraction for build, flash, and test operations.

MARA owns the interfaces; PlatformIO (and any future tool) is just an adapter.
"""

from .interfaces import BuildBackend, FlashBackend, TestBackend
from .models import (
    BuildRequest, BuildOutcome,
    FlashRequest, FlashOutcome,
    TestRequest, TestOutcome,
)
from .registry import BackendRegistry, get_registry

__all__ = [
    "BuildBackend", "FlashBackend", "TestBackend",
    "BuildRequest", "BuildOutcome",
    "FlashRequest", "FlashOutcome",
    "TestRequest", "TestOutcome",
    "BackendRegistry", "get_registry",
]
