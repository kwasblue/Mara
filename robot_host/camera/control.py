# robot_host/module/camera_control.py
"""Camera control API client for ESP32-CAM."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Dict, Any
import requests


class FrameSize(IntEnum):
    """ESP32-CAM frame size options."""
    R96X96 = 0
    QQVGA = 1      # 160x120
    R128X128 = 2
    QCIF = 3       # 176x144
    HQVGA = 4      # 240x176
    R240X240 = 5
    QVGA = 6       # 320x240
    CIF = 7        # 400x296
    HVGA = 8       # 480x320
    VGA = 9        # 640x480
    SVGA = 10      # 800x600
    XGA = 11       # 1024x768
    HD = 12        # 1280x720
    SXGA = 13      # 1280x1024
    UXGA = 14      # 1600x1200


@dataclass
class CameraConfig:
    """Camera configuration settings."""
    frame_size: FrameSize = FrameSize.VGA
    quality: int = 12          # 0-63, lower = better
    brightness: int = 0        # -2 to 2
    contrast: int = 0          # -2 to 2
    saturation: int = 0        # -2 to 2
    sharpness: int = 0         # -2 to 2
    hmirror: bool = False
    vflip: bool = False
    white_balance: bool = True
    awb_gain: bool = True
    wb_mode: int = 0           # 0-4
    exposure_ctrl: bool = True
    aec_value: int = 300       # 0-1200
    gain_ctrl: bool = True
    agc_gain: int = 0          # 0-30

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CameraConfig":
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
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frameSize": int(self.frame_size),
            "quality": self.quality,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "sharpness": self.sharpness,
            "hmirror": self.hmirror,
            "vflip": self.vflip,
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


class CameraControlClient:
    """
    Client for ESP32-CAM control API.

    Provides methods to:
    - Get/set camera configuration (resolution, quality, brightness, etc.)
    - Get/set motion detection settings
    - Get device status
    - Control flash LED
    - Reboot device
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        auth: Optional[tuple] = None,
    ):
        """
        :param base_url: Base URL of ESP32-CAM, e.g. "http://10.0.0.66"
        :param timeout: HTTP timeout in seconds
        :param auth: Optional (username, password) tuple for protected endpoints
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth = auth
        self.session = requests.Session()
        if auth:
            self.session.auth = auth

    def _get(self, path: str) -> Optional[Dict[str, Any]]:
        """GET request helper."""
        try:
            resp = self.session.get(
                f"{self.base_url}{path}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[CameraControl] GET {path} failed: {e}")
            return None

    def _post(self, path: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """POST request helper."""
        try:
            resp = self.session.post(
                f"{self.base_url}{path}",
                json=data,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[CameraControl] POST {path} failed: {e}")
            return None

    # ---------- Status ----------

    def get_status(self) -> Optional[DeviceStatus]:
        """Get device status."""
        data = self._get("/api/status")
        if data:
            return DeviceStatus.from_dict(data)
        return None

    def is_online(self) -> bool:
        """Check if camera is reachable."""
        return self.get_status() is not None

    # ---------- Camera Config ----------

    def get_camera_config(self) -> Optional[CameraConfig]:
        """Get current camera configuration."""
        data = self._get("/api/camera/config")
        if data:
            return CameraConfig.from_dict(data)
        return None

    def set_camera_config(self, config: CameraConfig) -> bool:
        """Set camera configuration."""
        result = self._post("/api/camera/config", config.to_dict())
        return result is not None

    def set_resolution(self, size: FrameSize) -> bool:
        """Set camera resolution."""
        return self._post("/api/camera/config", {"frameSize": int(size)}) is not None

    def set_quality(self, quality: int) -> bool:
        """Set JPEG quality (0-63, lower = better)."""
        return self._post("/api/camera/config", {"quality": quality}) is not None

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness (-2 to 2)."""
        return self._post("/api/camera/config", {"brightness": brightness}) is not None

    def set_contrast(self, contrast: int) -> bool:
        """Set contrast (-2 to 2)."""
        return self._post("/api/camera/config", {"contrast": contrast}) is not None

    def set_hmirror(self, enable: bool) -> bool:
        """Enable/disable horizontal mirror."""
        return self._post("/api/camera/config", {"hmirror": enable}) is not None

    def set_vflip(self, enable: bool) -> bool:
        """Enable/disable vertical flip."""
        return self._post("/api/camera/config", {"vflip": enable}) is not None

    def set_saturation(self, saturation: int) -> bool:
        """Set saturation (-2 to 2)."""
        return self._post("/api/camera/config", {"saturation": saturation}) is not None

    def set_sharpness(self, sharpness: int) -> bool:
        """Set sharpness (-2 to 2)."""
        return self._post("/api/camera/config", {"sharpness": sharpness}) is not None

    def set_whitebal(self, enable: bool) -> bool:
        """Enable/disable auto white balance."""
        return self._post("/api/camera/config", {"whiteBalance": enable}) is not None

    def set_wb_mode(self, mode: int) -> bool:
        """Set white balance mode (0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home)."""
        return self._post("/api/camera/config", {"wbMode": mode}) is not None

    def set_exposure_ctrl(self, enable: bool) -> bool:
        """Enable/disable auto exposure control."""
        return self._post("/api/camera/config", {"exposureCtrl": enable}) is not None

    def set_aec_value(self, value: int) -> bool:
        """Set manual exposure value (0-1200)."""
        return self._post("/api/camera/config", {"aecValue": value}) is not None

    def set_gain_ctrl(self, enable: bool) -> bool:
        """Enable/disable auto gain control."""
        return self._post("/api/camera/config", {"gainCtrl": enable}) is not None

    def set_agc_gain(self, gain: int) -> bool:
        """Set manual gain (0-30)."""
        return self._post("/api/camera/config", {"agcGain": gain}) is not None

    def set_gainceiling(self, ceiling: int) -> bool:
        """Set gain ceiling (0=2x to 6=128x)."""
        return self._post("/api/camera/config", {"gainCeiling": ceiling}) is not None

    # ---------- Flash Control ----------

    def toggle_flash(self) -> Optional[bool]:
        """Toggle flash LED. Returns new state or None on error."""
        result = self._post("/flash")
        if result:
            return result.get("flash", False)
        return None

    def set_flash(self, on: bool) -> bool:
        """Set flash to specific state."""
        status = self.get_status()
        if status is None:
            return False
        if status.flash_on != on:
            self.toggle_flash()
        return True

    # ---------- Motion Detection ----------

    def get_motion_config(self) -> Optional[MotionConfig]:
        """Get motion detection configuration."""
        data = self._get("/api/motion/config")
        if data:
            return MotionConfig.from_dict(data)
        return None

    def set_motion_config(self, config: MotionConfig) -> bool:
        """Set motion detection configuration."""
        result = self._post("/api/motion/config", config.to_dict())
        return result is not None

    def enable_motion_detection(self, sensitivity: int = 30) -> bool:
        """Enable motion detection with given sensitivity."""
        return self._post("/api/motion/config", {
            "enabled": True,
            "sensitivity": sensitivity,
        }) is not None

    def disable_motion_detection(self) -> bool:
        """Disable motion detection."""
        return self._post("/api/motion/config", {"enabled": False}) is not None

    # ---------- System ----------

    def reboot(self) -> bool:
        """Reboot the camera."""
        result = self._post("/api/reboot")
        return result is not None

    def factory_reset(self) -> bool:
        """Factory reset the camera (clears all saved settings)."""
        result = self._post("/api/factory-reset")
        return result is not None
