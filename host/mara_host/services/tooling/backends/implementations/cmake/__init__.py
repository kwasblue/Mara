# services/build/backends/cmake/__init__.py
"""CMake adapter for build, flash, and test operations.

This backend uses CMake for building and esptool for flashing.
Useful for ESP-IDF projects or any CMake-based embedded project.
"""

from .build_backend import CMakeBuildBackend
from .flash_backend import CMakeFlashBackend
from .test_backend import CMakeTestBackend

__all__ = [
    "CMakeBuildBackend",
    "CMakeFlashBackend",
    "CMakeTestBackend",
    "register_backends",
]


def register_backends(registry) -> None:
    """Register all CMake backends with *registry*."""
    registry.register_build("cmake", CMakeBuildBackend())
    registry.register_flash("cmake", CMakeFlashBackend())
    registry.register_test("cmake", CMakeTestBackend())
