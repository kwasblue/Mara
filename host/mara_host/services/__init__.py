# mara_host/services/__init__.py
"""
Services layer for mara_host.

AUTO-DISCOVERY: Services are lazily imported from subpackages.
To add a new service, create a package `services/myservice/` with
exports in `__init__.py`.

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
from typing import Any

# Known exports mapped to their source modules
# This enables: from mara_host.services import StateService
_EXPORTS = {
    # Control
    "StateService": "control",
    "RobotState": "control",
    "MotionService": "control",
    "Velocity": "control",
    "MotorService": "control",
    "MotorConfig": "control",
    "MotorState": "control",
    "ServoService": "control",
    "ServoConfig": "control",
    "ServoState": "control",
    "GpioService": "control",
    "GpioChannel": "control",
    "GpioMode": "control",
    "WifiService": "control",
    "ServiceResult": "control",
    # Telemetry
    "TelemetryService": "telemetry",
    "TelemetrySnapshot": "telemetry",
    "ImuData": "telemetry",
    "EncoderData": "telemetry",
    # Camera
    "StreamService": "camera",
    "CameraFrame": "camera",
    "CameraControlService": "camera",
    "CameraConfig": "camera",
    "Resolution": "camera",
    # Pins
    "PinService": "pins",
    "PinConflict": "pins",
    "PinRecommendation": "pins",
    "GroupRecommendation": "pins",
    # Testing
    "TestService": "testing",
    "TestResult": "testing",
    "TestStatus": "testing",
    "FirmwareTestService": "testing",
    "FirmwareTestResult": "testing",
    # Transport
    "ConnectionService": "transport",
    "ConnectionConfig": "transport",
    "ConnectionInfo": "transport",
    "TransportType": "transport",
    "RobotControlService": "transport",
    # Build
    "FirmwareBuildService": "build",
    "BuildResult": "build",
    "BuildStage": "build",
    "FirmwareSize": "build",
    # Codegen
    "CodeGeneratorService": "codegen",
    "GeneratorType": "codegen",
    "GeneratorResult": "codegen",
    # Recording
    "RecordingService": "recording",
    "ReplayService": "recording",
    "RecordingConfig": "recording",
    "SessionInfo": "recording",
    # Persistence
    "McuDiagnosticsService": "persistence",
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
