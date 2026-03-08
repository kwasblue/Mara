# mara_host/services/__init__.py
"""
Services layer for mara_host.

ROLE: Business logic extracted from CLI commands.
PURPOSE: Reusable from scripts, APIs, notebooks, and tests.

KEY PRINCIPLE: Services provide reusable operations for both
GUI and CLI interfaces.

Packages:
    control/    - State and motion services (StateService, MotionService)
    telemetry/  - Telemetry subscription and data access
    pins/       - GPIO pin management (PinService)
    transport/  - Connection and robot control services
    build/      - Firmware build orchestration
    codegen/    - Code generation services
    recording/  - Session recording and replay
    testing/    - Robot test suite

Example:
    from mara_host.services import StateService, MotionService
    from mara_host.services import TelemetryService

    # Control services
    state_svc = StateService(client)
    await state_svc.arm()

    motion_svc = MotionService(client)
    await motion_svc.set_velocity(0.5, 0.0)

    # Telemetry
    telem = TelemetryService(client)
    await telem.start()
    imu = telem.get_latest_imu()

Dependency rules (see docs/COMPOSITION.md):
    - services/ may depend on tools/, config/
    - services/ must NOT depend on cli/, runtime/
"""

# Control services (state, motion, hardware)
from mara_host.services.control import (
    StateService,
    RobotState,
    MotionService,
    Velocity,
    MotorService,
    MotorConfig,
    MotorState,
    ServoService,
    ServoConfig,
    ServoState,
    GpioService,
    GpioChannel,
    GpioMode,
    ServiceResult,
)

# Telemetry services
from mara_host.services.telemetry import (
    TelemetryService,
    TelemetrySnapshot,
    ImuData,
    EncoderData,
)

# Camera services
from mara_host.services.camera import (
    StreamService,
    CameraFrame,
    CameraControlService,
    CameraConfig,
    Resolution,
)

# Pin management
from mara_host.services.pins import (
    PinService,
    PinConflict,
    PinRecommendation,
    GroupRecommendation,
)

# Testing
from mara_host.services.testing import TestService, TestResult

# Transport and connection
from mara_host.services.transport import (
    ConnectionService,
    ConnectionConfig,
    ConnectionInfo,
    TransportType,
    RobotControlService,
)

# Build
from mara_host.services.build import (
    FirmwareBuildService,
    BuildResult,
    BuildStage,
    FirmwareSize,
)

# Code generation
from mara_host.services.codegen import (
    CodeGeneratorService,
    GeneratorType,
    GeneratorResult,
)

# Recording
from mara_host.services.recording import (
    RecordingService,
    ReplayService,
    RecordingConfig,
    SessionInfo,
)

__all__ = [
    # Control - State
    "StateService",
    "RobotState",
    # Control - Motion
    "MotionService",
    "Velocity",
    # Control - Motors
    "MotorService",
    "MotorConfig",
    "MotorState",
    # Control - Servos
    "ServoService",
    "ServoConfig",
    "ServoState",
    # Control - GPIO
    "GpioService",
    "GpioChannel",
    "GpioMode",
    # Control - Result
    "ServiceResult",
    # Telemetry
    "TelemetryService",
    "TelemetrySnapshot",
    "ImuData",
    "EncoderData",
    # Camera
    "StreamService",
    "CameraFrame",
    "CameraControlService",
    "CameraConfig",
    "Resolution",
    # Pins
    "PinService",
    "PinConflict",
    "PinRecommendation",
    "GroupRecommendation",
    # Testing
    "TestService",
    "TestResult",
    # Transport
    "ConnectionService",
    "ConnectionConfig",
    "ConnectionInfo",
    "TransportType",
    "RobotControlService",
    # Build
    "FirmwareBuildService",
    "BuildResult",
    "BuildStage",
    "FirmwareSize",
    # Codegen
    "CodeGeneratorService",
    "GeneratorType",
    "GeneratorResult",
    # Recording
    "RecordingService",
    "ReplayService",
    "RecordingConfig",
    "SessionInfo",
]
