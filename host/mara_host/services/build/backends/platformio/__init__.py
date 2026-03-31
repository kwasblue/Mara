# services/build/backends/platformio/__init__.py
"""PlatformIO adapter — the ONLY place in MARA that may touch ``pio``."""

from .test_backend import PlatformIOTestBackend

__all__ = ["PlatformIOTestBackend", "register_backends"]


def register_backends(registry) -> None:
    """Register all PlatformIO backends with *registry*."""
    registry.register_test("platformio", PlatformIOTestBackend())
