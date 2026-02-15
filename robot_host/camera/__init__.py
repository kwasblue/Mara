# robot_host/camera/__init__.py
"""
Camera subsystem for robot host.

Integrates ESP32-CAM into the robot host architecture with:
- EventBus integration for commands and frame publishing
- Support for multiple cameras
- Polling and streaming capture modes
- Recording support
- ML preprocessing
- Preset configurations

Usage:
    from robot_host.core.event_bus import EventBus
    from robot_host.camera import CameraHostModule

    bus = EventBus()
    camera = CameraHostModule(bus, cameras={0: "http://10.0.0.66"})

    # Subscribe to frames
    bus.subscribe("camera.frame.0", lambda f: print(f"Frame: {f.sequence}"))

    # Send commands via bus
    bus.publish("cmd.camera", {"cmd": "CMD_CAM_START_CAPTURE", "camera_id": 0})
    bus.publish("cmd.camera", {"cmd": "CMD_CAM_APPLY_PRESET", "camera_id": 0, "preset": "streaming"})
"""

# Host module (EventBus integration)
from .host_module import CameraHostModule

# Models
from .models import (
    CameraConfig as HostCameraConfig,
    CameraStatus,
    CameraFrame,
    MLFrame,
    CameraStats,
    MotionEvent,
    CaptureMode,
    FrameSize as HostFrameSize,
)

# Presets
from .presets import get_preset, list_presets, PRESETS

# Client (standalone camera client)
from .client import Esp32CamClient, FrameResult

# Streaming
from .stream import MjpegStreamClient, StreamFrame

# Control
from .control import (
    CameraControlClient,
    CameraConfig,
    MotionConfig,
    DeviceStatus,
    FrameSize,
)

# Stats
from .stats import StatsTracker, CameraStatistics, FrameStats

# Recording
from .recorder import FrameRecorder, MotionTriggeredRecorder, RecordingMetadata

# High-level module
from .module import CameraModule

# Manager (multi-camera)
from .manager import CameraManager, CameraState, CameraInfo, MultiFrameResult

# Async clients
from .async_client import AsyncCameraClient, AsyncMjpegClient, AsyncFrame

__all__ = [
    # Host module
    "CameraHostModule",
    # Host models
    "HostCameraConfig",
    "CameraStatus",
    "CameraFrame",
    "MLFrame",
    "CameraStats",
    "MotionEvent",
    "CaptureMode",
    "HostFrameSize",
    # Presets
    "get_preset",
    "list_presets",
    "PRESETS",
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
    # Manager
    "CameraManager",
    "CameraState",
    "CameraInfo",
    "MultiFrameResult",
    # Async
    "AsyncCameraClient",
    "AsyncMjpegClient",
    "AsyncFrame",
]
