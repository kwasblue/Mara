# mara_host/services/__init__.py
"""
Services layer for mara_host.

ROLE: Business logic extracted from CLI commands.
PURPOSE: Reusable from scripts, APIs, notebooks, and tests.

KEY PRINCIPLE: Services do NOT require a robot connection.
They operate on configuration, files, and external resources.

For robot control, use Robot or Runtime directly.

Packages:
    pins/       - GPIO pin management (PinService)
    transport/  - Connection and robot control services
    build/      - Firmware build orchestration
    codegen/    - Code generation services
    recording/  - Session recording and replay
    testing/    - Robot test suite

Example:
    from mara_host.services.pins import PinService

    service = PinService()
    conflicts = service.detect_conflicts()
    rec = service.recommend_motor_pins("LEFT")

Dependency rules (see docs/COMPOSITION.md):
    - services/ may depend on tools/, config/
    - services/ must NOT depend on cli/, runtime/
"""

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
