# robot_host/module/camera/host_module.py
"""
Camera host module - integrates ESP32-CAM into robot host architecture.

Subscribes to camera commands via EventBus and publishes frames/events.
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Dict, Any, Callable

import numpy as np

from robot_host.core.event_bus import EventBus
from robot_host.camera.client import Esp32CamClient
from robot_host.camera.stream import MjpegStreamClient
from robot_host.camera.stats import StatsTracker
from robot_host.camera.recorder import FrameRecorder
from robot_host.vision.ml_preprocess import preprocess_for_ml

from .models import (
    CameraConfig, CameraStatus, CameraFrame, MLFrame,
    CameraStats, MotionEvent, CaptureMode, FrameSize,
)
from .presets import get_preset, list_presets


class CameraHostModule:
    """
    Integrates ESP32-CAM into robot host architecture.

    Features:
    - EventBus integration for commands and frame publishing
    - Supports multiple cameras
    - Polling and streaming capture modes
    - Recording support
    - ML preprocessing
    - Preset configurations

    Topics published:
    - camera.frame.<id>: CameraFrame with BGR image
    - camera.ml_frame.<id>: MLFrame with preprocessed data
    - camera.status.<id>: CameraStatus updates
    - camera.motion.<id>: MotionEvent when motion detected
    - camera.stats.<id>: CameraStats periodic updates

    Topics subscribed:
    - cmd.camera: Camera commands (CMD_CAM_*)
    """

    def __init__(
        self,
        bus: EventBus,
        cameras: Optional[Dict[int, str]] = None,
        ml_size: tuple[int, int] = (224, 224),
        stream_port: int = 81,
    ) -> None:
        """
        Initialize camera host module.

        :param bus: EventBus instance
        :param cameras: Dict mapping camera_id to base_url, e.g. {0: "http://10.0.0.66"}
        :param ml_size: Target size for ML preprocessing
        :param stream_port: Port for MJPEG streaming
        """
        self._bus = bus
        self._ml_size = ml_size
        self._stream_port = stream_port

        # Camera clients indexed by camera_id
        self._clients: Dict[int, Esp32CamClient] = {}
        self._stream_clients: Dict[int, MjpegStreamClient] = {}
        self._recorders: Dict[int, FrameRecorder] = {}

        # State tracking
        self._configs: Dict[int, CameraConfig] = {}
        self._status: Dict[int, CameraStatus] = {}
        self._capture_mode: Dict[int, CaptureMode] = {}
        self._capturing: Dict[int, bool] = {}
        self._sequence: Dict[int, int] = {}

        # Capture threads
        self._capture_threads: Dict[int, threading.Thread] = {}
        self._stop_events: Dict[int, threading.Event] = {}
        self._target_fps: Dict[int, float] = {}

        # Initialize cameras
        if cameras:
            for cam_id, url in cameras.items():
                self.add_camera(cam_id, url)

        # Subscribe to commands
        bus.subscribe("cmd.camera", self._on_command)

    # ---------- Camera Management ----------

    def add_camera(self, camera_id: int, base_url: str) -> None:
        """Add a camera to the module."""
        self._clients[camera_id] = Esp32CamClient(base_url)
        self._configs[camera_id] = CameraConfig()
        self._status[camera_id] = CameraStatus(camera_id=camera_id)
        self._capture_mode[camera_id] = CaptureMode.POLLING
        self._capturing[camera_id] = False
        self._sequence[camera_id] = 0
        self._stop_events[camera_id] = threading.Event()
        self._target_fps[camera_id] = 10.0

        # Try to get initial status
        self._update_status(camera_id)

    def remove_camera(self, camera_id: int) -> None:
        """Remove a camera from the module."""
        self.stop_capture(camera_id)
        self._clients.pop(camera_id, None)
        self._stream_clients.pop(camera_id, None)
        self._configs.pop(camera_id, None)
        self._status.pop(camera_id, None)

    def get_camera_ids(self) -> list[int]:
        """Get list of registered camera IDs."""
        return list(self._clients.keys())

    # ---------- Command Handler ----------

    def _on_command(self, msg: Dict[str, Any]) -> None:
        """Handle camera commands from EventBus."""
        cmd = msg.get("cmd", "")
        camera_id = msg.get("camera_id", 0)

        if camera_id not in self._clients:
            self._bus.publish("camera.error", {
                "camera_id": camera_id,
                "error": f"Unknown camera_id: {camera_id}",
            })
            return

        try:
            if cmd == "CMD_CAM_GET_STATUS":
                self._update_status(camera_id)

            elif cmd == "CMD_CAM_GET_CONFIG":
                self._publish_config(camera_id)

            elif cmd == "CMD_CAM_SET_RESOLUTION":
                self._set_resolution(camera_id, msg.get("size", 8))

            elif cmd == "CMD_CAM_SET_QUALITY":
                self._set_quality(camera_id, msg.get("quality", 12))

            elif cmd == "CMD_CAM_SET_BRIGHTNESS":
                self._set_brightness(camera_id, msg.get("brightness", 0))

            elif cmd == "CMD_CAM_SET_CONTRAST":
                self._set_contrast(camera_id, msg.get("contrast", 0))

            elif cmd == "CMD_CAM_SET_SATURATION":
                self._set_saturation(camera_id, msg.get("saturation", 0))

            elif cmd == "CMD_CAM_SET_SHARPNESS":
                self._set_sharpness(camera_id, msg.get("sharpness", 0))

            elif cmd == "CMD_CAM_SET_FLIP":
                self._set_flip(camera_id, msg.get("hmirror", False), msg.get("vflip", False))

            elif cmd == "CMD_CAM_SET_AWB":
                self._set_awb(camera_id, msg.get("enabled", True), msg.get("mode", 0))

            elif cmd == "CMD_CAM_SET_EXPOSURE":
                self._set_exposure(camera_id, msg.get("auto", True), msg.get("value", 300))

            elif cmd == "CMD_CAM_SET_GAIN":
                self._set_gain(camera_id, msg.get("auto", True), msg.get("value", 0), msg.get("ceiling", 2))

            elif cmd == "CMD_CAM_FLASH":
                self._set_flash(camera_id, msg.get("state", "toggle"))

            elif cmd == "CMD_CAM_APPLY_PRESET":
                self._apply_preset(camera_id, msg.get("preset", "default"))

            elif cmd == "CMD_CAM_START_CAPTURE":
                mode_str = msg.get("mode", "polling")
                mode = CaptureMode.STREAMING if mode_str == "streaming" else CaptureMode.POLLING
                fps = msg.get("fps", 10.0)
                self.start_capture(camera_id, mode, fps)

            elif cmd == "CMD_CAM_STOP_CAPTURE":
                self.stop_capture(camera_id)

            elif cmd == "CMD_CAM_CAPTURE_FRAME":
                publish = msg.get("publish", True)
                self.capture_single(camera_id, publish=publish)

            elif cmd == "CMD_CAM_START_RECORDING":
                output_dir = msg.get("output_dir", "recordings")
                fmt = msg.get("format", "video")
                self.start_recording(camera_id, output_dir, fmt)

            elif cmd == "CMD_CAM_STOP_RECORDING":
                self.stop_recording(camera_id)

            elif cmd == "CMD_CAM_SET_MOTION_DETECTION":
                enabled = msg.get("enabled", False)
                sensitivity = msg.get("sensitivity", 30)
                self._set_motion_detection(camera_id, enabled, sensitivity)

        except Exception as e:
            self._bus.publish("camera.error", {
                "camera_id": camera_id,
                "cmd": cmd,
                "error": str(e),
            })

    # ---------- Camera Settings ----------

    def _set_resolution(self, camera_id: int, size: int) -> None:
        client = self._clients[camera_id]
        if client.set_resolution(FrameSize(size)):
            self._configs[camera_id].frame_size = FrameSize(size)
            self._publish_config(camera_id)

    def _set_quality(self, camera_id: int, quality: int) -> None:
        client = self._clients[camera_id]
        if client.set_quality(quality):
            self._configs[camera_id].quality = quality
            self._publish_config(camera_id)

    def _set_brightness(self, camera_id: int, brightness: int) -> None:
        client = self._clients[camera_id]
        if client.control.set_brightness(brightness):
            self._configs[camera_id].brightness = brightness

    def _set_contrast(self, camera_id: int, contrast: int) -> None:
        client = self._clients[camera_id]
        if client.control.set_contrast(contrast):
            self._configs[camera_id].contrast = contrast

    def _set_saturation(self, camera_id: int, saturation: int) -> None:
        client = self._clients[camera_id]
        if client.control.set_saturation(saturation):
            self._configs[camera_id].saturation = saturation

    def _set_sharpness(self, camera_id: int, sharpness: int) -> None:
        client = self._clients[camera_id]
        if client.control.set_sharpness(sharpness):
            self._configs[camera_id].sharpness = sharpness

    def _set_flip(self, camera_id: int, hmirror: bool, vflip: bool) -> None:
        client = self._clients[camera_id]
        client.control.set_hmirror(hmirror)
        client.control.set_vflip(vflip)
        self._configs[camera_id].hmirror = hmirror
        self._configs[camera_id].vflip = vflip

    def _set_awb(self, camera_id: int, enabled: bool, mode: int) -> None:
        client = self._clients[camera_id]
        client.control.set_whitebal(enabled)
        if enabled:
            client.control.set_wb_mode(mode)
        self._configs[camera_id].awb_enabled = enabled
        self._configs[camera_id].awb_mode = mode

    def _set_exposure(self, camera_id: int, auto: bool, value: int) -> None:
        client = self._clients[camera_id]
        client.control.set_exposure_ctrl(auto)
        if not auto:
            client.control.set_aec_value(value)
        self._configs[camera_id].aec_enabled = auto
        self._configs[camera_id].aec_value = value

    def _set_gain(self, camera_id: int, auto: bool, value: int, ceiling: int) -> None:
        client = self._clients[camera_id]
        client.control.set_gain_ctrl(auto)
        if not auto:
            client.control.set_agc_gain(value)
        client.control.set_gainceiling(ceiling)
        self._configs[camera_id].agc_enabled = auto
        self._configs[camera_id].agc_gain = value
        self._configs[camera_id].gain_ceiling = ceiling

    def _set_flash(self, camera_id: int, state: str) -> None:
        client = self._clients[camera_id]
        if state == "on":
            client.set_flash(True)
            self._status[camera_id].flash_on = True
        elif state == "off":
            client.set_flash(False)
            self._status[camera_id].flash_on = False
        elif state == "toggle":
            new_state = client.toggle_flash()
            if new_state is not None:
                self._status[camera_id].flash_on = new_state

    def _apply_preset(self, camera_id: int, preset_name: str) -> None:
        """Apply a preset configuration."""
        config = get_preset(preset_name)
        client = self._clients[camera_id]

        # Apply all settings
        client.set_resolution(config.frame_size)
        client.set_quality(config.quality)
        client.control.set_brightness(config.brightness)
        client.control.set_contrast(config.contrast)
        client.control.set_saturation(config.saturation)
        client.control.set_sharpness(config.sharpness)
        client.control.set_hmirror(config.hmirror)
        client.control.set_vflip(config.vflip)
        client.control.set_whitebal(config.awb_enabled)
        client.control.set_wb_mode(config.awb_mode)
        client.control.set_exposure_ctrl(config.aec_enabled)
        client.control.set_aec_value(config.aec_value)
        client.control.set_gain_ctrl(config.agc_enabled)
        client.control.set_agc_gain(config.agc_gain)
        client.control.set_gainceiling(config.gain_ceiling)

        self._configs[camera_id] = config
        self._publish_config(camera_id)

    def _set_motion_detection(self, camera_id: int, enabled: bool, sensitivity: int) -> None:
        client = self._clients[camera_id]
        if enabled:
            client.enable_motion_detection(sensitivity)
        else:
            client.disable_motion_detection()

    # ---------- Status & Config Publishing ----------

    def _update_status(self, camera_id: int) -> None:
        """Fetch and publish camera status."""
        client = self._clients[camera_id]
        device_status = client.get_status()

        if device_status:
            status = self._status[camera_id]
            status.connected = True
            status.ip = device_status.ip
            status.hostname = device_status.hostname
            status.rssi = device_status.rssi
            status.free_heap = device_status.free_heap
            status.uptime_seconds = device_status.uptime_seconds
            status.flash_on = device_status.flash_on
            status.streaming = self._capturing.get(camera_id, False)
            status.recording = camera_id in self._recorders
        else:
            self._status[camera_id].connected = False

        self._bus.publish(f"camera.status.{camera_id}", self._status[camera_id])

    def _publish_config(self, camera_id: int) -> None:
        """Publish current camera configuration."""
        self._bus.publish(f"camera.config.{camera_id}", self._configs[camera_id])

    def _publish_stats(self, camera_id: int) -> None:
        """Publish capture statistics."""
        client = self._clients[camera_id]
        stats = client.get_stats()
        cam_stats = CameraStats(
            camera_id=camera_id,
            total_frames=stats.total_frames,
            successful_frames=stats.successful_frames,
            failed_frames=stats.failed_frames,
            avg_fps=stats.avg_fps,
            avg_latency_ms=stats.avg_latency_ms,
            success_rate=stats.success_rate,
            total_bytes=stats.total_bytes,
        )
        self._bus.publish(f"camera.stats.{camera_id}", cam_stats)

    # ---------- Capture Control ----------

    def start_capture(
        self,
        camera_id: int,
        mode: CaptureMode = CaptureMode.POLLING,
        fps: float = 10.0,
    ) -> None:
        """Start continuous frame capture."""
        if self._capturing.get(camera_id):
            return

        self._capture_mode[camera_id] = mode
        self._target_fps[camera_id] = fps
        self._capturing[camera_id] = True
        self._stop_events[camera_id].clear()

        if mode == CaptureMode.STREAMING:
            self._start_streaming(camera_id)
        else:
            self._start_polling(camera_id)

        self._status[camera_id].streaming = True
        self._bus.publish(f"camera.status.{camera_id}", self._status[camera_id])

    def stop_capture(self, camera_id: int) -> None:
        """Stop continuous frame capture."""
        if not self._capturing.get(camera_id):
            return

        self._stop_events[camera_id].set()
        self._capturing[camera_id] = False

        # Stop streaming client if running
        if camera_id in self._stream_clients:
            self._stream_clients[camera_id].stop()
            del self._stream_clients[camera_id]

        # Wait for capture thread
        if camera_id in self._capture_threads:
            self._capture_threads[camera_id].join(timeout=2.0)
            del self._capture_threads[camera_id]

        self._status[camera_id].streaming = False
        self._bus.publish(f"camera.status.{camera_id}", self._status[camera_id])

    def capture_single(self, camera_id: int, publish: bool = True) -> Optional[CameraFrame]:
        """Capture a single frame."""
        client = self._clients[camera_id]
        result = client._fetch_raw_bgr()

        if not result.success or result.frame is None:
            return None

        self._sequence[camera_id] += 1
        frame = CameraFrame(
            camera_id=camera_id,
            data=result.frame,
            timestamp=result.timestamp,
            sequence=self._sequence[camera_id],
            size_bytes=result.size_bytes,
            latency_ms=result.latency_ms,
        )

        if publish:
            self._publish_frame(camera_id, frame)

        return frame

    def _start_polling(self, camera_id: int) -> None:
        """Start polling capture thread."""
        thread = threading.Thread(
            target=self._polling_loop,
            args=(camera_id,),
            name=f"CameraPolling-{camera_id}",
            daemon=True,
        )
        self._capture_threads[camera_id] = thread
        thread.start()

    def _polling_loop(self, camera_id: int) -> None:
        """Polling capture loop."""
        stop_event = self._stop_events[camera_id]
        target_period = 1.0 / self._target_fps[camera_id]

        while not stop_event.is_set():
            t0 = time.time()
            self.capture_single(camera_id, publish=True)

            # Throttle to target FPS
            elapsed = time.time() - t0
            sleep_time = target_period - elapsed
            if sleep_time > 0:
                stop_event.wait(sleep_time)

    def _start_streaming(self, camera_id: int) -> None:
        """Start MJPEG streaming."""
        client = self._clients[camera_id]
        stream = MjpegStreamClient(client.base_url, stream_port=self._stream_port)

        def on_frame(stream_frame):
            self._sequence[camera_id] += 1
            frame = CameraFrame(
                camera_id=camera_id,
                data=stream_frame.data,
                timestamp=stream_frame.timestamp,
                sequence=self._sequence[camera_id],
                size_bytes=stream_frame.size_bytes,
            )
            self._publish_frame(camera_id, frame)

        stream.set_on_frame(on_frame)
        self._stream_clients[camera_id] = stream
        stream.start()

    def _publish_frame(self, camera_id: int, frame: CameraFrame) -> None:
        """Publish frame and ML-preprocessed frame."""
        # Publish raw frame
        self._bus.publish(f"camera.frame.{camera_id}", frame)

        # Create and publish ML frame
        ml_data = preprocess_for_ml(
            frame.data,
            target_size=self._ml_size,
            normalize=True,
            to_chw=True,
        )
        if ml_data is not None:
            ml_frame = MLFrame(
                camera_id=camera_id,
                data=ml_data,
                timestamp=frame.timestamp,
                sequence=frame.sequence,
                original_size=(frame.data.shape[0], frame.data.shape[1]),
            )
            self._bus.publish(f"camera.ml_frame.{camera_id}", ml_frame)

        # Record if recording
        if camera_id in self._recorders:
            self._recorders[camera_id].add_frame(frame.data, frame.timestamp)

    # ---------- Recording ----------

    def start_recording(
        self,
        camera_id: int,
        output_dir: str = "recordings",
        format: str = "video",
    ) -> Optional[str]:
        """Start recording frames."""
        if camera_id in self._recorders:
            return None

        recorder = FrameRecorder(
            output_dir=output_dir,
            prefix=f"camera_{camera_id}",
            fps=self._target_fps.get(camera_id, 10.0),
            format=format,
        )
        path = recorder.start(source=self._clients[camera_id].base_url)
        self._recorders[camera_id] = recorder
        self._status[camera_id].recording = True
        return path

    def stop_recording(self, camera_id: int) -> None:
        """Stop recording."""
        if camera_id in self._recorders:
            self._recorders[camera_id].stop()
            del self._recorders[camera_id]
            self._status[camera_id].recording = False

    # ---------- Cleanup ----------

    def shutdown(self) -> None:
        """Stop all captures and cleanup."""
        for camera_id in list(self._clients.keys()):
            self.stop_capture(camera_id)
            self.stop_recording(camera_id)
