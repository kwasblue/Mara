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


# Mapping of attribute names to (module_name, attr_name) for lazy loading
# module_name is relative to this package; if attr_name is None, use name as-is
_LAZY_IMPORTS = {
    # Host module
    "CameraHostModule": ("host_module", "CameraHostModule"),
    # Models
    "FrameSize": ("models", None),
    "CaptureMode": ("models", None),
    "StreamPreset": ("models", None),
    "CameraConfig": ("models", None),
    "MotionConfig": ("models", None),
    "DeviceStatus": ("models", None),
    "CameraStatus": ("models", None),
    "StreamStats": ("models", None),
    "CameraStats": ("models", None),
    "CameraFrame": ("models", None),
    "MLFrame": ("models", None),
    "MotionEvent": ("models", None),
    # Presets
    "get_preset": ("presets", None),
    "list_presets": ("presets", None),
    "PRESETS": ("presets", None),
    # Client
    "Esp32CamClient": ("client", None),
    "FrameResult": ("client", None),
    # Streaming
    "MjpegStreamClient": ("stream", None),
    "StreamFrame": ("stream", None),
    # Control
    "CameraControlClient": ("control", "CameraControlClient"),
    # Stats
    "StatsTracker": ("stats", None),
    "CameraStatistics": ("stats", None),
    "FrameStats": ("stats", None),
    # Recording
    "FrameRecorder": ("recorder", None),
    "MotionTriggeredRecorder": ("recorder", None),
    "RecordingMetadata": ("recorder", None),
    # Module
    "CameraModule": ("module", "CameraModule"),
    # Manager
    "CameraManager": ("manager", None),
    "CameraState": ("manager", None),
    "CameraInfo": ("manager", None),
    "MultiFrameResult": ("manager", None),
    # Async
    "AsyncCameraClient": ("async_client", None),
    "AsyncMjpegClient": ("async_client", None),
    "AsyncFrame": ("async_client", None),
}


def __getattr__(name: str):
    """Lazy import with dependency check - O(1) lookup."""
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'mara_host.camera' has no attribute '{name}'")

    _check_vision_deps()

    module_name, attr_name = _LAZY_IMPORTS[name]
    import importlib
    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, attr_name or name)


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
