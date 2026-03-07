# mara_host/camera/models.py
"""
Canonical data models for camera subsystem.

This module is the single source of truth for all camera-related types.
All other camera files should import from here.
"""

from dataclasses import dataclass, asdict, field
from enum import IntEnum
from typing import Optional, Dict, Any
import numpy as np


# =============================================================================
# ENUMS (firmware-compatible)
# =============================================================================

class FrameSize(IntEnum):
    """
    ESP32-CAM frame size (matches firmware framesize_t).

    These values MUST match the ESP32-CAM firmware exactly.
    Reference: esp_camera.h framesize_t enum
    """
    R96X96 = 0      # 96x96
    QQVGA = 1       # 160x120
    R128X128 = 2    # 128x128
    QCIF = 3        # 176x144
    HQVGA = 4       # 240x176
    R240X240 = 5    # 240x240
    QVGA = 6        # 320x240
    CIF = 7         # 400x296
    HVGA = 8        # 480x320
    VGA = 9         # 640x480
    SVGA = 10       # 800x600
    XGA = 11        # 1024x768
    HD = 12         # 1280x720
    SXGA = 13       # 1280x1024
    UXGA = 14       # 1600x1200


class CaptureMode(IntEnum):
    """
    Frame capture mode (matches firmware protocol).

    POLLING: HTTP polling of /jpg endpoint (single frame)
    STREAMING: MJPEG stream from /stream endpoint (continuous)
    """
    POLLING = 0
    STREAMING = 1


class StreamPreset(IntEnum):
    """Streaming resolution presets for bandwidth control."""
    HIGH = 0       # VGA 640x480, quality 10
    MEDIUM = 1     # CIF 400x296, quality 12
    LOW = 2        # QVGA 320x240, quality 15
    MINIMAL = 3    # QQVGA 160x120, quality 20


# =============================================================================
# CONFIGURATION (device settings)
# =============================================================================

@dataclass
class CameraConfig:
    """
    Camera configuration settings.

    Field names match the ESP32-CAM HTTP API for direct serialization.
    """
    frame_size: FrameSize = FrameSize.VGA
    quality: int = 12          # 0-63, lower = better JPEG quality
    brightness: int = 0        # -2 to 2
    contrast: int = 0          # -2 to 2
    saturation: int = 0        # -2 to 2
    sharpness: int = 0         # -2 to 2
    hmirror: bool = False
    vflip: bool = False
    # Auto white balance
    white_balance: bool = True
    awb_gain: bool = True
    wb_mode: int = 0           # 0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home
    # Auto exposure
    exposure_ctrl: bool = True
    aec_value: int = 300       # 0-1200 manual exposure
    # Auto gain
    gain_ctrl: bool = True
    agc_gain: int = 0          # 0-30 manual gain
    gain_ceiling: int = 2      # 0=2x to 6=128x

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CameraConfig":
        """Create config from HTTP API response dict."""
        return cls(
            frame_size=FrameSize(d.get("frameSize", 9)),
            quality=d.get("quality", 12),
            brightness=d.get("brightness", 0),
            contrast=d.get("contrast", 0),
            saturation=d.get("saturation", 0),
            sharpness=d.get("sharpness", 0),
            hmirror=d.get("hmirror", False),
            vflip=d.get("vflip", False),
            white_balance=d.get("whiteBalance", True),
            awb_gain=d.get("awbGain", True),
            wb_mode=d.get("wbMode", 0),
            exposure_ctrl=d.get("exposureCtrl", True),
            aec_value=d.get("aecValue", 300),
            gain_ctrl=d.get("gainCtrl", True),
            agc_gain=d.get("agcGain", 0),
            gain_ceiling=d.get("gainCeiling", 2),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to HTTP API request dict."""
        return {
            "frameSize": int(self.frame_size),
            "quality": self.quality,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "sharpness": self.sharpness,
            "hmirror": self.hmirror,
            "vflip": self.vflip,
            "whiteBalance": self.white_balance,
            "awbGain": self.awb_gain,
            "wbMode": self.wb_mode,
            "exposureCtrl": self.exposure_ctrl,
            "aecValue": self.aec_value,
            "gainCtrl": self.gain_ctrl,
            "agcGain": self.agc_gain,
            "gainCeiling": self.gain_ceiling,
        }


@dataclass
class MotionConfig:
    """Motion detection configuration."""
    enabled: bool = False
    sensitivity: int = 30      # 0-100
    threshold: int = 15
    cooldown_ms: int = 5000

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MotionConfig":
        return cls(
            enabled=d.get("enabled", False),
            sensitivity=d.get("sensitivity", 30),
            threshold=d.get("threshold", 15),
            cooldown_ms=d.get("cooldownMs", 5000),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "sensitivity": self.sensitivity,
            "threshold": self.threshold,
            "cooldownMs": self.cooldown_ms,
        }


# =============================================================================
# STATUS / STATS (runtime state)
# =============================================================================

@dataclass
class DeviceStatus:
    """ESP32-CAM device status."""
    hostname: str = ""
    ip: str = ""
    rssi: int = 0
    mac: str = ""
    free_heap: int = 0
    uptime_seconds: int = 0
    flash_on: bool = False
    ap_mode: bool = False
    motion_enabled: bool = False
    last_motion: int = 0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DeviceStatus":
        return cls(
            hostname=d.get("hostname", ""),
            ip=d.get("ip", ""),
            rssi=d.get("rssi", 0),
            mac=d.get("mac", ""),
            free_heap=d.get("freeHeap", 0),
            uptime_seconds=d.get("uptime", 0),
            flash_on=d.get("flashOn", False),
            ap_mode=d.get("apMode", False),
            motion_enabled=d.get("motionEnabled", False),
            last_motion=d.get("lastMotion", 0),
        )


@dataclass
class CameraStatus:
    """Camera module status (host-side tracking)."""
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
class StreamStats:
    """Streaming performance statistics from ESP32-CAM."""
    total_frames: int = 0
    dropped_frames: int = 0
    error_frames: int = 0
    current_fps: float = 0.0
    avg_latency_ms: float = 0.0
    total_bytes: int = 0
    uptime_seconds: int = 0
    active_clients: int = 0
    current_quality: int = 12
    target_fps: int = 30
    quality_scaling: bool = True
    preset: int = 0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StreamStats":
        return cls(
            total_frames=d.get("totalFrames", 0),
            dropped_frames=d.get("droppedFrames", 0),
            error_frames=d.get("errorFrames", 0),
            current_fps=d.get("currentFps", 0.0),
            avg_latency_ms=d.get("avgLatencyMs", 0.0),
            total_bytes=d.get("totalBytes", 0),
            uptime_seconds=d.get("uptimeSeconds", 0),
            active_clients=d.get("activeClients", 0),
            current_quality=d.get("currentQuality", 12),
            target_fps=d.get("targetFps", 30),
            quality_scaling=d.get("qualityScaling", True),
            preset=d.get("preset", 0),
        )

    @property
    def drop_rate(self) -> float:
        """Calculate frame drop rate as percentage."""
        total = self.total_frames + self.dropped_frames
        if total == 0:
            return 0.0
        return (self.dropped_frames / total) * 100

    @property
    def total_mb(self) -> float:
        """Total bytes transferred in MB."""
        return self.total_bytes / (1024 * 1024)


@dataclass
class CameraStats:
    """Frame capture statistics (host-side)."""
    camera_id: int = 0
    total_frames: int = 0
    successful_frames: int = 0
    failed_frames: int = 0
    avg_fps: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_bytes: int = 0


# =============================================================================
# EVENTS (EventBus payloads)
# =============================================================================

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
class MotionEvent:
    """Motion detection event."""
    camera_id: int
    timestamp: float
    intensity: float  # 0.0 to 1.0
