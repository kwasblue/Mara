# robot_host/module/__init__.py
"""
Camera and ML modules for robot_host.
"""

# Camera client
from robot_host.module.camera_client import (
    Esp32CamClient,
    FrameResult,
)

# Camera streaming
from robot_host.module.camera_stream import (
    MjpegStreamClient,
    StreamFrame,
)

# Camera control
from robot_host.module.camera_control import (
    CameraControlClient,
    CameraConfig,
    MotionConfig,
    DeviceStatus,
    FrameSize,
)

# Camera statistics
from robot_host.module.camera_stats import (
    StatsTracker,
    CameraStatistics,
    FrameStats,
)

# Camera recording
from robot_host.module.camera_recorder import (
    FrameRecorder,
    MotionTriggeredRecorder,
    RecordingMetadata,
)

# Camera module (high-level)
from robot_host.module.camera_module import (
    CameraModule,
    CaptureMode,
)

# Multi-camera manager
from robot_host.module.camera_manager import (
    CameraManager,
    CameraState,
    CameraInfo,
    MultiFrameResult,
)

# Async clients
from robot_host.module.camera_async import (
    AsyncCameraClient,
    AsyncMjpegClient,
    AsyncFrame,
)

# Camera host module (EventBus integration)
from robot_host.module.camera import (
    CameraHostModule,
    CameraFrame,
    MLFrame,
    CameraStats as HostCameraStats,
    MotionEvent,
    get_preset,
    list_presets,
    PRESETS,
)

__all__ = [
    # Client
    "Esp32CamClient",
    "FrameResult",
    # Streaming
    "MjpegStreamClient",
    "StreamFrame",
    # Control
    "CameraControlClient",
    "CameraConfig",
    "MotionConfig",
    "DeviceStatus",
    "FrameSize",
    # Stats
    "StatsTracker",
    "CameraStatistics",
    "FrameStats",
    # Recording
    "FrameRecorder",
    "MotionTriggeredRecorder",
    "RecordingMetadata",
    # Module
    "CameraModule",
    "CaptureMode",
    # Manager
    "CameraManager",
    "CameraState",
    "CameraInfo",
    "MultiFrameResult",
    # Async
    "AsyncCameraClient",
    "AsyncMjpegClient",
    "AsyncFrame",
    # Host module
    "CameraHostModule",
    "CameraFrame",
    "MLFrame",
    "HostCameraStats",
    "MotionEvent",
    "get_preset",
    "list_presets",
    "PRESETS",
]
