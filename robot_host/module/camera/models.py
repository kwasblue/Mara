# robot_host/module/camera/models.py
"""Data models for camera subsystem."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
import numpy as np


class FrameSize(IntEnum):
    """Camera resolution presets (matches ESP32-CAM framesize_t)."""
    QQVGA = 0    # 160x120
    QQVGA2 = 1   # 128x160
    QCIF = 2     # 176x144
    HQVGA = 3    # 240x176
    QVGA_240 = 4 # 240x240
    QVGA = 5     # 320x240
    CIF = 6      # 400x296
    HVGA = 7     # 480x320
    VGA = 8      # 640x480
    SVGA = 9     # 800x600
    XGA = 10     # 1024x768
    HD = 11      # 1280x720
    SXGA = 12    # 1280x1024
    UXGA = 13    # 1600x1200


class CaptureMode(IntEnum):
    """Frame capture mode."""
    POLLING = 0    # HTTP polling /jpg endpoint
    STREAMING = 1  # MJPEG stream /stream endpoint


@dataclass
class CameraConfig:
    """Camera hardware configuration."""
    frame_size: FrameSize = FrameSize.VGA
    quality: int = 12  # JPEG quality (4-63, lower=better)
    brightness: int = 0  # -2 to 2
    contrast: int = 0  # -2 to 2
    saturation: int = 0  # -2 to 2
    sharpness: int = 0  # -2 to 2
    hmirror: bool = False
    vflip: bool = False
    awb_enabled: bool = True
    awb_mode: int = 0  # 0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home
    aec_enabled: bool = True  # Auto exposure
    aec_value: int = 300  # Manual exposure (0-1200)
    agc_enabled: bool = True  # Auto gain
    agc_gain: int = 0  # Manual gain (0-30)
    gain_ceiling: int = 2  # 0=2x, 1=4x, 2=8x, etc.


@dataclass
class CameraStatus:
    """Camera device status."""
    camera_id: int = 0
    connected: bool = False
    ip: str = ""
    hostname: str = ""
    rssi: int = 0  # WiFi signal strength
    free_heap: int = 0
    uptime_seconds: int = 0
    flash_on: bool = False
    streaming: bool = False
    recording: bool = False


@dataclass
class CameraFrame:
    """A captured frame with metadata."""
    camera_id: int
    data: np.ndarray  # BGR image
    timestamp: float
    sequence: int
    size_bytes: int
    latency_ms: float = 0.0


@dataclass
class MLFrame:
    """ML-ready preprocessed frame."""
    camera_id: int
    data: np.ndarray  # CHW float32 normalized
    timestamp: float
    sequence: int
    original_size: tuple  # (H, W) of source frame


@dataclass
class CameraStats:
    """Frame capture statistics."""
    camera_id: int = 0
    total_frames: int = 0
    successful_frames: int = 0
    failed_frames: int = 0
    avg_fps: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_bytes: int = 0


@dataclass
class MotionEvent:
    """Motion detection event."""
    camera_id: int
    timestamp: float
    intensity: float  # 0.0 to 1.0
