# robot_host/module/camera/__init__.py
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
    from robot_host.module.camera import CameraHostModule

    bus = EventBus()
    camera = CameraHostModule(bus, cameras={0: "http://10.0.0.66"})

    # Subscribe to frames
    bus.subscribe("camera.frame.0", lambda f: print(f"Frame: {f.sequence}"))

    # Send commands via bus
    bus.publish("cmd.camera", {"cmd": "CMD_CAM_START_CAPTURE", "camera_id": 0})
    bus.publish("cmd.camera", {"cmd": "CMD_CAM_APPLY_PRESET", "camera_id": 0, "preset": "streaming"})
"""

from .host_module import CameraHostModule
from .models import (
    CameraConfig,
    CameraStatus,
    CameraFrame,
    MLFrame,
    CameraStats,
    MotionEvent,
    CaptureMode,
    FrameSize,
)
from .presets import get_preset, list_presets, PRESETS

__all__ = [
    # Main module
    "CameraHostModule",
    # Models
    "CameraConfig",
    "CameraStatus",
    "CameraFrame",
    "MLFrame",
    "CameraStats",
    "MotionEvent",
    "CaptureMode",
    "FrameSize",
    # Presets
    "get_preset",
    "list_presets",
    "PRESETS",
]
