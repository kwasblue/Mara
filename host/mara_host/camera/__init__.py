# mara_host/camera/__init__.py
"""
Camera subsystem for robot host.

REQUIRES: Install with vision extras: pip install mara-host[vision]

Integrates ESP32-CAM into the robot host architecture with:
- EventBus integration for commands and frame publishing
- Support for multiple cameras
- Polling and streaming capture modes
- Recording support
- ML preprocessing
- Preset configurations

Usage:
    from mara_host.core.event_bus import EventBus
    from mara_host.camera import CameraHostModule

    bus = EventBus()
    camera = CameraHostModule(bus, cameras={0: "http://10.0.0.66"})

    # Subscribe to frames
    bus.subscribe("camera.frame.0", lambda f: print(f"Frame: {f.sequence}"))

    # Send commands via bus
    bus.publish("cmd.camera", {"cmd": "CMD_CAM_START_CAPTURE", "camera_id": 0})
    bus.publish("cmd.camera", {"cmd": "CMD_CAM_APPLY_PRESET", "camera_id": 0, "preset": "streaming"})
"""

try:
    import numpy as np
    import cv2
    _HAS_VISION_DEPS = True
except ImportError as e:
    _HAS_VISION_DEPS = False
    _IMPORT_ERROR = e


def _check_vision_deps():
    """Raise helpful error if vision dependencies not installed."""
    if not _HAS_VISION_DEPS:
        raise ImportError(
            "Camera module requires vision dependencies. "
            "Install with: pip install mara-host[vision]\n"
            f"Missing: {_IMPORT_ERROR}"
        )


def __getattr__(name: str):
    """Lazy import with dependency check."""
    _check_vision_deps()

    # Import the actual module
    if name == "CameraHostModule":
        from .host_module import CameraHostModule
        return CameraHostModule
    elif name in ("FrameSize", "CaptureMode", "StreamPreset", "CameraConfig",
                  "MotionConfig", "DeviceStatus", "CameraStatus", "StreamStats",
                  "CameraStats", "CameraFrame", "MLFrame", "MotionEvent"):
        from . import models
        return getattr(models, name)
    elif name in ("get_preset", "list_presets", "PRESETS"):
        from . import presets
        return getattr(presets, name)
    elif name in ("Esp32CamClient", "FrameResult"):
        from . import client
        return getattr(client, name)
    elif name in ("MjpegStreamClient", "StreamFrame"):
        from . import stream
        return getattr(stream, name)
    elif name == "CameraControlClient":
        from .control import CameraControlClient
        return CameraControlClient
    elif name in ("StatsTracker", "CameraStatistics", "FrameStats"):
        from . import stats
        return getattr(stats, name)
    elif name in ("FrameRecorder", "MotionTriggeredRecorder", "RecordingMetadata"):
        from . import recorder
        return getattr(recorder, name)
    elif name == "CameraModule":
        from .module import CameraModule
        return CameraModule
    elif name in ("CameraManager", "CameraState", "CameraInfo", "MultiFrameResult"):
        from . import manager
        return getattr(manager, name)
    elif name in ("AsyncCameraClient", "AsyncMjpegClient", "AsyncFrame"):
        from . import async_client
        return getattr(async_client, name)

    raise AttributeError(f"module 'mara_host.camera' has no attribute '{name}'")


__all__ = [
    # Host module
    "CameraHostModule",
    # Enums
    "FrameSize",
    "CaptureMode",
    "StreamPreset",
    # Configuration
    "CameraConfig",
    "MotionConfig",
    # Status
    "DeviceStatus",
    "CameraStatus",
    "StreamStats",
    "CameraStats",
    # Events
    "CameraFrame",
    "MLFrame",
    "MotionEvent",
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
