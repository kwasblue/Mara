# mara_host/services/camera/camera_control_service.py
"""
Camera control service.

Provides high-level control for camera settings.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class Resolution(IntEnum):
    """Camera resolution presets (ESP32-CAM frame sizes)."""

    QQVGA = 0  # 160x120
    QCIF = 2  # 176x144
    HQVGA = 3  # 240x176
    QVGA = 5  # 320x240
    CIF = 6  # 400x296
    VGA = 8  # 640x480
    SVGA = 9  # 800x600
    XGA = 10  # 1024x768
    SXGA = 12  # 1280x1024
    UXGA = 13  # 1600x1200

    @property
    def dimensions(self) -> tuple[int, int]:
        """Get (width, height) for this resolution."""
        dims = {
            0: (160, 120),
            2: (176, 144),
            3: (240, 176),
            5: (320, 240),
            6: (400, 296),
            8: (640, 480),
            9: (800, 600),
            10: (1024, 768),
            12: (1280, 1024),
            13: (1600, 1200),
        }
        return dims.get(self.value, (640, 480))


@dataclass
class CameraConfig:
    """Camera configuration."""

    camera_id: int = 0
    resolution: Resolution = Resolution.VGA
    quality: int = 10  # 4-63, lower is better
    brightness: int = 0  # -2 to 2
    contrast: int = 0  # -2 to 2
    saturation: int = 0  # -2 to 2
    sharpness: int = 0  # -2 to 2
    hmirror: bool = False
    vflip: bool = False
    awb_enabled: bool = True
    awb_mode: int = 0  # 0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home
    auto_exposure: bool = True
    exposure_value: int = 300
    auto_gain: bool = True
    gain_value: int = 0
    gain_ceiling: int = 2  # 0=2x to 6=128x
    flash_on: bool = False


class CameraControlService:
    """
    Service for camera control.

    Manages camera settings like resolution, quality,
    brightness, and image adjustments.

    Example:
        camera = CameraControlService(client)

        # Set resolution
        await camera.set_resolution(Resolution.VGA)

        # Adjust quality
        await camera.set_quality(10)

        # Apply preset
        await camera.apply_preset("streaming")

        # Get current config
        config = camera.get_config()
    """

    def __init__(self, client: "MaraClient", camera_id: int = 0):
        """
        Initialize camera control service.

        Args:
            client: Connected MaraClient instance
            camera_id: Camera ID for multi-camera setups
        """
        self.client = client
        self.camera_id = camera_id
        self._config = CameraConfig(camera_id=camera_id)

    def get_config(self) -> CameraConfig:
        """Get current camera configuration."""
        return self._config

    async def set_resolution(self, resolution: Resolution | int) -> ServiceResult:
        """
        Set camera resolution.

        Args:
            resolution: Resolution enum or frame size value

        Returns:
            ServiceResult
        """
        size = resolution.value if isinstance(resolution, Resolution) else resolution

        ok, error = await self.client.send_reliable(
            "CMD_CAM_SET_RESOLUTION",
            {"camera_id": self.camera_id, "size": size},
        )

        if ok:
            self._config.resolution = Resolution(size)
            return ServiceResult.success(
                data={
                    "resolution": size,
                    "dimensions": self._config.resolution.dimensions,
                }
            )
        else:
            return ServiceResult.failure(error=error or "Failed to set resolution")

    async def set_quality(self, quality: int) -> ServiceResult:
        """
        Set JPEG quality.

        Args:
            quality: Quality value (4-63, lower is better)

        Returns:
            ServiceResult
        """
        quality = max(4, min(63, quality))

        ok, error = await self.client.send_reliable(
            "CMD_CAM_SET_QUALITY",
            {"camera_id": self.camera_id, "quality": quality},
        )

        if ok:
            self._config.quality = quality
            return ServiceResult.success(data={"quality": quality})
        else:
            return ServiceResult.failure(error=error or "Failed to set quality")

    async def set_brightness(self, brightness: int) -> ServiceResult:
        """
        Set image brightness.

        Args:
            brightness: Brightness level (-2 to 2)

        Returns:
            ServiceResult
        """
        brightness = max(-2, min(2, brightness))

        ok, error = await self.client.send_reliable(
            "CMD_CAM_SET_BRIGHTNESS",
            {"camera_id": self.camera_id, "brightness": brightness},
        )

        if ok:
            self._config.brightness = brightness
            return ServiceResult.success(data={"brightness": brightness})
        else:
            return ServiceResult.failure(error=error or "Failed to set brightness")

    async def set_contrast(self, contrast: int) -> ServiceResult:
        """
        Set image contrast.

        Args:
            contrast: Contrast level (-2 to 2)

        Returns:
            ServiceResult
        """
        contrast = max(-2, min(2, contrast))

        ok, error = await self.client.send_reliable(
            "CMD_CAM_SET_CONTRAST",
            {"camera_id": self.camera_id, "contrast": contrast},
        )

        if ok:
            self._config.contrast = contrast
            return ServiceResult.success(data={"contrast": contrast})
        else:
            return ServiceResult.failure(error=error or "Failed to set contrast")

    async def set_saturation(self, saturation: int) -> ServiceResult:
        """
        Set color saturation.

        Args:
            saturation: Saturation level (-2 to 2)

        Returns:
            ServiceResult
        """
        saturation = max(-2, min(2, saturation))

        ok, error = await self.client.send_reliable(
            "CMD_CAM_SET_SATURATION",
            {"camera_id": self.camera_id, "saturation": saturation},
        )

        if ok:
            self._config.saturation = saturation
            return ServiceResult.success(data={"saturation": saturation})
        else:
            return ServiceResult.failure(error=error or "Failed to set saturation")

    async def set_flip(
        self,
        hmirror: Optional[bool] = None,
        vflip: Optional[bool] = None,
    ) -> ServiceResult:
        """
        Set image flip/mirror options.

        Args:
            hmirror: Horizontal mirror (None = don't change)
            vflip: Vertical flip (None = don't change)

        Returns:
            ServiceResult
        """
        payload = {"camera_id": self.camera_id}
        if hmirror is not None:
            payload["hmirror"] = hmirror
        if vflip is not None:
            payload["vflip"] = vflip

        ok, error = await self.client.send_reliable("CMD_CAM_SET_FLIP", payload)

        if ok:
            if hmirror is not None:
                self._config.hmirror = hmirror
            if vflip is not None:
                self._config.vflip = vflip
            return ServiceResult.success(
                data={"hmirror": self._config.hmirror, "vflip": self._config.vflip}
            )
        else:
            return ServiceResult.failure(error=error or "Failed to set flip")

    async def set_flash(self, state: str | bool) -> ServiceResult:
        """
        Control flash LED.

        Args:
            state: "on", "off", "toggle", or bool

        Returns:
            ServiceResult
        """
        if isinstance(state, bool):
            state = "on" if state else "off"

        ok, error = await self.client.send_reliable(
            "CMD_CAM_FLASH",
            {"camera_id": self.camera_id, "state": state},
        )

        if ok:
            if state == "on":
                self._config.flash_on = True
            elif state == "off":
                self._config.flash_on = False
            else:  # toggle
                self._config.flash_on = not self._config.flash_on
            return ServiceResult.success(data={"flash": self._config.flash_on})
        else:
            return ServiceResult.failure(error=error or "Failed to control flash")

    async def apply_preset(self, preset: str) -> ServiceResult:
        """
        Apply a camera configuration preset.

        Args:
            preset: Preset name (default, streaming, high_quality, fast, night, ml_inference)

        Returns:
            ServiceResult
        """
        valid_presets = [
            "default",
            "streaming",
            "high_quality",
            "fast",
            "night",
            "ml_inference",
        ]
        if preset not in valid_presets:
            return ServiceResult.failure(
                error=f"Invalid preset. Valid: {', '.join(valid_presets)}"
            )

        ok, error = await self.client.send_reliable(
            "CMD_CAM_APPLY_PRESET",
            {"camera_id": self.camera_id, "preset": preset},
        )

        if ok:
            return ServiceResult.success(data={"preset": preset})
        else:
            return ServiceResult.failure(error=error or f"Failed to apply preset {preset}")

    async def capture_frame(self, publish: bool = True) -> ServiceResult:
        """
        Capture a single frame.

        Args:
            publish: Publish frame to event bus

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CAM_CAPTURE_FRAME",
            {"camera_id": self.camera_id, "publish": publish},
        )

        if ok:
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to capture frame")

    async def get_status(self) -> ServiceResult:
        """
        Get camera device status.

        Returns:
            ServiceResult with status data
        """
        ok, error = await self.client.send_reliable(
            "CMD_CAM_GET_STATUS",
            {"camera_id": self.camera_id},
        )

        if ok:
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to get camera status")

    async def start_capture(
        self,
        mode: str = "polling",
        fps: float = 10.0,
    ) -> ServiceResult:
        """
        Start continuous frame capture.

        Args:
            mode: Capture mode ("polling" or "streaming")
            fps: Target frame rate (polling mode)

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CAM_START_CAPTURE",
            {"camera_id": self.camera_id, "mode": mode, "fps": fps},
        )

        if ok:
            return ServiceResult.success(data={"mode": mode, "fps": fps})
        else:
            return ServiceResult.failure(error=error or "Failed to start capture")

    async def stop_capture(self) -> ServiceResult:
        """
        Stop continuous frame capture.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_CAM_STOP_CAPTURE",
            {"camera_id": self.camera_id},
        )

        if ok:
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to stop capture")
