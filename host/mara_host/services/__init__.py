# mara_host/services/__init__.py
"""
Services layer for mara_host.

AUTO-DISCOVERY: Services are automatically discovered from subpackages.
To add a new service, create a package `services/myservice/` with
exports in `__init__.py`. No manual registration required!

Example:
    # services/myservice/__init__.py
    from .myservice import MyService, MyConfig
    __all__ = ["MyService", "MyConfig"]

Then use it:
    from mara_host.services import MyService
    # or
    from mara_host.services.myservice import MyService

Packages:
    control/    - State and motion services
    telemetry/  - Telemetry subscription and data access
    camera/     - Camera streaming and control
    pins/       - GPIO pin management
    transport/  - Connection and robot control
    build/      - Firmware build orchestration
    codegen/    - Code generation services
    recording/  - Session recording and replay
    testing/    - Robot test suite
"""

import importlib
from pathlib import Path
from typing import Any


def _discover_services() -> dict[str, str]:
    """Auto-discover services from subpackages.

    Scans services/*/ subdirectories and looks for classes ending with
    'Service', 'Config', or 'State' in their __all__ or public attributes.

    Returns:
        dict mapping export name to subpackage name
    """
    discovered: dict[str, str] = {}
    services_dir = Path(__file__).parent

    for subdir in sorted(services_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        init_file = subdir / "__init__.py"
        if not init_file.exists():
            continue

        # Import subpackage and find exportable classes
        try:
            module = importlib.import_module(f"mara_host.services.{subdir.name}")
            # Prefer __all__ if defined, otherwise use dir()
            names = getattr(module, "__all__", None)
            if names is None:
                names = [n for n in dir(module) if not n.startswith("_")]

            for name in names:
                # Auto-discover Service, Config, State, Result, and Response classes
                if (
                    name.endswith("Service")
                    or name.endswith("Config")
                    or name.endswith("State")
                    or name.endswith("Result")
                    or name.endswith("Response")
                    or name.endswith("Status")
                    or name.endswith("Info")
                    or name.endswith("Data")
                    or name.endswith("Type")
                ):
                    discovered[name] = subdir.name
        except ImportError:
            # Skip packages that fail to import
            pass

    return discovered


# Manual exports for backward compatibility and special cases
# These take precedence over auto-discovered exports
_MANUAL_EXPORTS = {
    # Response types (direct import from types.py)
    "GpioReadResponse": "types",
    "GpioWriteResponse": "types",
    "GpioRegisterResponse": "types",
    "EncoderReadResponse": "types",
    "EncoderAttachResponse": "types",
    "ServoAttachResponse": "types",
    "ServoSetAngleResponse": "types",
    "MotorSetSpeedResponse": "types",
    "MotorAttachResponse": "types",
    "ImuReadResponse": "types",
    "RobotStateResponse": "types",
    "ControlGraphSlotStatus": "types",
    "ControlGraphStatus": "types",
}

# Merge discovered with manual exports (manual takes precedence)
_DISCOVERED = _discover_services()
_EXPORTS = {**_DISCOVERED, **_MANUAL_EXPORTS}

# Cache for imported modules
_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import of service classes."""
    if name in _EXPORTS:
        subpackage = _EXPORTS[name]

        # Import from cache or load
        if subpackage not in _cache:
            _cache[subpackage] = importlib.import_module(
                f".{subpackage}", package=__name__
            )

        return getattr(_cache[subpackage], name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available exports."""
    return list(_EXPORTS.keys())


__all__ = list(_EXPORTS.keys())
