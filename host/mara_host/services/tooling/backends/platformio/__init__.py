# services/build/backends/platformio/__init__.py
"""PlatformIO adapter — the ONLY place in MARA that may touch ``pio``."""

from .build_backend import PlatformIOBuildBackend
from .flash_backend import PlatformIOFlashBackend
from .test_backend import PlatformIOTestBackend

__all__ = [
    "PlatformIOBuildBackend",
    "PlatformIOFlashBackend",
    "PlatformIOTestBackend",
    "register_backends",
]


def register_backends(registry) -> None:
    """Register all PlatformIO backends with *registry*."""
    registry.register_build("platformio", PlatformIOBuildBackend())
    registry.register_flash("platformio", PlatformIOFlashBackend())
    registry.register_test("platformio", PlatformIOTestBackend())
