# services/build/backends/registry.py
"""Simple backend registry — register by name, look up by name.

Backends auto-register when their module is imported.  The CLI or service
layer calls ``get_registry()`` and picks a backend by name (defaulting to
``"platformio"``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces import BuildBackend, FlashBackend, TestBackend


class BackendRegistry:
    """Singleton registry for build / flash / test backends."""

    def __init__(self) -> None:
        self._build: dict[str, BuildBackend] = {}
        self._flash: dict[str, FlashBackend] = {}
        self._test: dict[str, TestBackend] = {}

    # -- registration -------------------------------------------------------

    def register_build(self, name: str, backend: BuildBackend) -> None:
        self._build[name] = backend

    def register_flash(self, name: str, backend: FlashBackend) -> None:
        self._flash[name] = backend

    def register_test(self, name: str, backend: TestBackend) -> None:
        self._test[name] = backend

    # -- lookup -------------------------------------------------------------

    def get_build(self, name: str = "platformio") -> BuildBackend:
        return self._build[name]

    def get_flash(self, name: str = "platformio") -> FlashBackend:
        return self._flash[name]

    def get_test(self, name: str = "platformio") -> TestBackend:
        return self._test[name]

    # -- introspection ------------------------------------------------------

    def list_build_backends(self) -> list[str]:
        return list(self._build)

    def list_flash_backends(self) -> list[str]:
        return list(self._flash)

    def list_test_backends(self) -> list[str]:
        return list(self._test)


# Module-level singleton
_registry = BackendRegistry()


def get_registry() -> BackendRegistry:
    """Return the global backend registry, loading defaults on first call."""
    if not _registry.list_test_backends():
        # Auto-import the PlatformIO adapters so they self-register
        try:
            from .platformio import register_backends  # noqa: F811
            register_backends(_registry)
        except ImportError:
            pass
    return _registry
