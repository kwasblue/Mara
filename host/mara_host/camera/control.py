# mara_host/camera/control.py
"""Camera control API client for ESP32-CAM."""

from typing import Optional, Dict, Any
import requests

# Import canonical types from models
from .models import (
    FrameSize,
    StreamPreset,
    CameraConfig,
    MotionConfig,
    DeviceStatus,
    StreamStats,
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

    # ---------- Streaming Control ----------

    def get_stream_stats(self) -> Optional[StreamStats]:
        """Get streaming performance statistics."""
        data = self._get("/api/stream/stats")
        if data:
            return StreamStats.from_dict(data)
        return None

    def set_stream_preset(self, preset: StreamPreset) -> bool:
        """
        Set streaming resolution preset.

        Presets:
        - HIGH: VGA 640x480, quality 10
        - MEDIUM: CIF 400x296, quality 12
        - LOW: QVGA 320x240, quality 15
        - MINIMAL: QQVGA 160x120, quality 20
        """
        result = self._post("/api/stream/preset", {"preset": int(preset)})
        return result is not None

    def set_stream_config(
        self,
        target_fps: Optional[int] = None,
        quality_scaling: Optional[bool] = None,
        reset_stats: bool = False,
    ) -> bool:
        """
        Configure streaming settings.

        :param target_fps: Target frames per second (0 = unlimited)
        :param quality_scaling: Enable/disable dynamic quality based on client count
        :param reset_stats: Reset streaming statistics
        """
        config = {}
        if target_fps is not None:
            config["targetFps"] = target_fps
        if quality_scaling is not None:
            config["qualityScaling"] = quality_scaling
        if reset_stats:
            config["resetStats"] = True

        if not config:
            return True  # Nothing to update

        result = self._post("/api/stream/config", config)
        return result is not None

    def set_low_bandwidth_mode(self, enabled: bool = True) -> bool:
        """
        Enable or disable low bandwidth mode.

        Low bandwidth: QVGA (320x240), 15 FPS, quality scaling enabled
        Normal: VGA (640x480), 30 FPS
        """
        if enabled:
            self.set_stream_preset(StreamPreset.LOW)
            return self.set_stream_config(target_fps=15, quality_scaling=True)
        else:
            self.set_stream_preset(StreamPreset.HIGH)
            return self.set_stream_config(target_fps=30, quality_scaling=True)
