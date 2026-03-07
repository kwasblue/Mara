# mara_host/camera/module.py
"""
Enhanced CameraModule with streaming, recording, and ML integration.
"""

import threading
import time
from typing import Callable, Optional, Tuple

import cv2
import numpy as np

from mara_host.camera.client import Esp32CamClient, FrameResult
from mara_host.camera.stream import MjpegStreamClient, StreamFrame
from mara_host.camera.control import CameraControlClient
from mara_host.camera.stats import StatsTracker, CameraStatistics
from mara_host.camera.recorder import FrameRecorder, MotionTriggeredRecorder
from mara_host.vision.ml_preprocess import preprocess_for_ml

# Import canonical types from models
from .models import FrameSize, CaptureMode, DeviceStatus


# Callback signatures
FrameCallback = Callable[[np.ndarray, np.ndarray, float], None]
# (display_frame, ml_frame, timestamp)

RawFrameCallback = Callable[[np.ndarray, float], None]
# (raw_frame, timestamp)

MotionCallback = Callable[[float], None]
# (timestamp)


class CameraModule:
    """
    Enhanced CameraModule with:
    - Polling or MJPEG streaming modes
    - Live preview window (optional)
    - ML preprocessing
    - Frame statistics
    - Recording support
    - Camera control API
    - Motion detection callbacks
    """

    def __init__(
        self,
        base_url: str,
        name: str = "front_cam",
        mode: CaptureMode = CaptureMode.POLLING,
        display_size: Tuple[int, int] = (320, 240),
        ml_size: Tuple[int, int] = (224, 224),
        blur_ksize: int = 0,
        fps: float = 10.0,
        show_preview: bool = False,
        show_stats: bool = True,
        frame_callback: Optional[FrameCallback] = None,
        raw_frame_callback: Optional[RawFrameCallback] = None,
        auth: Optional[Tuple[str, str]] = None,
        stream_port: int = 81,
    ) -> None:
        """
        :param base_url: Base URL of ESP32-CAM, like "http://10.0.0.66"
        :param name: Logical name of the camera for logging/events
        :param mode: CaptureMode.POLLING or CaptureMode.STREAMING
        :param display_size: (w, h) for display frames
        :param ml_size: (w, h) for ML frames
        :param blur_ksize: Gaussian blur kernel size for display (0 = none)
        :param fps: Target capture rate (for polling mode)
        :param show_preview: If True, opens an OpenCV window
        :param show_stats: If True, overlay stats on preview
        :param frame_callback: Called per frame with (display, ml, timestamp)
        :param raw_frame_callback: Called per frame with (raw, timestamp)
        :param auth: Optional (username, password) for API
        :param stream_port: Port for MJPEG streaming (default 81)
        """
        self.name = name
        self.base_url = base_url
        self.stream_port = stream_port
        self.mode = mode
        self.display_size = display_size
        self.ml_size = ml_size
        self.blur_ksize = blur_ksize
        self.target_fps = fps
        self.target_period = 1.0 / fps if fps > 0 else 0.0
        self.show_preview = show_preview
        self.show_stats = show_stats
        self.frame_callback = frame_callback
        self.raw_frame_callback = raw_frame_callback

        # Clients
        self.polling_client = Esp32CamClient(base_url, auth=auth)
        self.stream_client: Optional[MjpegStreamClient] = None
        self.control = CameraControlClient(base_url, auth=auth)

        # Statistics
        self.stats = StatsTracker()

        # Recording
        self._recorder: Optional[FrameRecorder] = None
        self._motion_recorder: Optional[MotionTriggeredRecorder] = None

        # Threading
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # Frame state
        self._last_frame: Optional[np.ndarray] = None
        self._last_display_frame: Optional[np.ndarray] = None
        self._last_ml_frame: Optional[np.ndarray] = None
        self._last_frame_time: float = 0.0
        self._frame_lock = threading.Lock()

        # Motion callback
        self._on_motion: Optional[MotionCallback] = None

    # ---------- Properties ----------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._last_frame.copy() if self._last_frame is not None else None

    @property
    def last_display_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._last_display_frame.copy() if self._last_display_frame is not None else None

    @property
    def last_ml_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._last_ml_frame.copy() if self._last_ml_frame is not None else None

    @property
    def window_name(self) -> str:
        return f"cam:{self.name}"

    # ---------- Public Control API ----------

    def start(self) -> None:
        """Start capture in a background thread."""
        if self._running:
            return

        self._stop_event.clear()
        self._running = True

        if self.mode == CaptureMode.STREAMING:
            self._start_streaming()
        else:
            self._thread = threading.Thread(
                target=self._polling_loop,
                name=f"CameraModule-{self.name}",
                daemon=True,
            )
            self._thread.start()

        mode_name = "streaming" if self.mode == CaptureMode.STREAMING else "polling"
        print(f"[CameraModule:{self.name}] Started in {mode_name} mode")

    def stop(self) -> None:
        """Stop capture."""
        self._stop_event.set()
        self._running = False

        if self.stream_client:
            self.stream_client.stop()

        if self._thread:
            self._thread.join(timeout=2.0)

        if self._recorder:
            self._recorder.stop()

        if self.show_preview:
            try:
                cv2.destroyWindow(self.window_name)
            except Exception:
                pass

        print(f"[CameraModule:{self.name}] Stopped")

    def run_foreground(self) -> None:
        """
        Run the capture loop on the current (main) thread.
        Required for OpenCV GUI on macOS.
        """
        self._stop_event.clear()
        self._running = True

        if self.mode == CaptureMode.STREAMING:
            self._streaming_foreground()
        else:
            self._polling_loop()

    # ---------- Mode Control ----------

    def set_mode(self, mode: CaptureMode) -> None:
        """Switch capture mode (stops and restarts if running)."""
        was_running = self._running
        if was_running:
            self.stop()

        self.mode = mode

        if was_running:
            self.start()

    # ---------- Camera Control ----------

    def set_resolution(self, size: FrameSize) -> bool:
        """Set camera resolution."""
        return self.control.set_resolution(size)

    def set_quality(self, quality: int) -> bool:
        """Set JPEG quality (0-63)."""
        return self.control.set_quality(quality)

    def toggle_flash(self) -> Optional[bool]:
        """Toggle flash LED."""
        return self.control.toggle_flash()

    def get_status(self) -> Optional[DeviceStatus]:
        """Get device status."""
        return self.control.get_status()

    def get_stats(self) -> CameraStatistics:
        """Get frame statistics."""
        return self.stats.get_stats()

    # ---------- Recording ----------

    def start_recording(
        self,
        output_dir: str = "recordings",
        fps: float = 0,  # 0 = use capture fps
        format: str = "video",
        **kwargs,
    ) -> Optional[str]:
        """
        Start recording frames.

        :return: Path to recording output
        """
        if self._recorder and self._recorder.is_recording:
            return None

        self._recorder = FrameRecorder(
            output_dir=output_dir,
            prefix=self.name,
            fps=fps or self.target_fps,
            format=format,
            **kwargs,
        )
        return self._recorder.start(source=self.base_url)

    def stop_recording(self) -> None:
        """Stop recording."""
        if self._recorder:
            self._recorder.stop()
            self._recorder = None

    def is_recording(self) -> bool:
        """Check if recording."""
        return self._recorder is not None and self._recorder.is_recording

    def enable_motion_recording(
        self,
        output_dir: str = "recordings/motion",
        pre_buffer_seconds: float = 2.0,
        post_buffer_seconds: float = 5.0,
    ) -> None:
        """Enable motion-triggered recording."""
        self._motion_recorder = MotionTriggeredRecorder(
            output_dir=output_dir,
            prefix=f"{self.name}_motion",
            fps=self.target_fps,
            pre_buffer_seconds=pre_buffer_seconds,
            post_buffer_seconds=post_buffer_seconds,
        )

    def trigger_motion_recording(self) -> Optional[str]:
        """Manually trigger motion recording."""
        if self._motion_recorder:
            return self._motion_recorder.trigger()
        return None

    # ---------- Callbacks ----------

    def set_frame_callback(self, callback: Optional[FrameCallback]) -> None:
        """Set callback for processed frames (display, ml, timestamp)."""
        self.frame_callback = callback

    def set_raw_frame_callback(self, callback: Optional[RawFrameCallback]) -> None:
        """Set callback for raw frames."""
        self.raw_frame_callback = callback

    def set_motion_callback(self, callback: Optional[MotionCallback]) -> None:
        """Set callback for motion events."""
        self._on_motion = callback

    # ---------- Internal: Polling Mode ----------

    def _polling_loop(self) -> None:
        """Polling capture loop."""
        print(f"[CameraModule:{self.name}] Polling loop started")

        if self.show_preview:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        while not self._stop_event.is_set():
            t0 = time.time()
            self._capture_frame_polling()
            self._throttle(t0)

        print(f"[CameraModule:{self.name}] Polling loop stopped")

    def _capture_frame_polling(self) -> None:
        """Capture and process a single frame via polling."""
        result = self.polling_client._fetch_raw_bgr()

        if not result.success or result.frame is None:
            self.stats.record_failure(result.error or "unknown")
            return

        self.stats.record_success(result.latency_ms, result.size_bytes)
        self._process_frame(result.frame, result.timestamp)

    # ---------- Internal: Streaming Mode ----------

    def _start_streaming(self) -> None:
        """Start MJPEG streaming."""
        self.stream_client = MjpegStreamClient(self.base_url, stream_port=self.stream_port)
        self.stream_client.set_on_frame(self._handle_stream_frame)
        self.stream_client.start()

        # Start display thread if needed
        if self.show_preview:
            self._thread = threading.Thread(
                target=self._display_loop,
                name=f"CameraModule-{self.name}-Display",
                daemon=True,
            )
            self._thread.start()

    def _handle_stream_frame(self, frame: StreamFrame) -> None:
        """Handle frame from MJPEG stream."""
        self.stats.record_success(0, frame.size_bytes)  # Latency tracked by stream client
        self._process_frame(frame.data, frame.timestamp)

    def _streaming_foreground(self) -> None:
        """Run streaming with foreground display."""
        self.stream_client = MjpegStreamClient(self.base_url, stream_port=self.stream_port)
        self.stream_client.set_on_frame(self._handle_stream_frame)
        self.stream_client.start()

        if self.show_preview:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        while not self._stop_event.is_set():
            if self.show_preview:
                display = self.last_display_frame
                if display is not None:
                    self._show_frame(display)
                if cv2.waitKey(16) & 0xFF == ord('q'):
                    self._stop_event.set()
            else:
                time.sleep(0.1)

        self.stream_client.stop()

    def _display_loop(self) -> None:
        """Background display loop for streaming mode."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        while not self._stop_event.is_set():
            display = self.last_display_frame
            if display is not None:
                self._show_frame(display)
            if cv2.waitKey(16) & 0xFF == ord('q'):
                self._stop_event.set()

    # ---------- Internal: Frame Processing ----------

    def _process_frame(self, raw_frame: np.ndarray, timestamp: float) -> None:
        """Process a captured frame."""
        # Create display frame
        display_frame = raw_frame.copy()
        if self.display_size:
            display_frame = cv2.resize(display_frame, self.display_size, interpolation=cv2.INTER_AREA)
        if self.blur_ksize and self.blur_ksize > 1:
            k = self.blur_ksize if self.blur_ksize % 2 == 1 else self.blur_ksize + 1
            display_frame = cv2.GaussianBlur(display_frame, (k, k), 0)

        # Create ML frame
        ml_frame = preprocess_for_ml(
            raw_frame,
            target_size=self.ml_size,
            normalize=True,
            to_chw=True,
        )

        # Store frames
        with self._frame_lock:
            self._last_frame = raw_frame
            self._last_display_frame = display_frame
            self._last_ml_frame = ml_frame
            self._last_frame_time = timestamp

        # Recording
        if self._recorder and self._recorder.is_recording:
            self._recorder.add_frame(raw_frame, timestamp)

        if self._motion_recorder:
            self._motion_recorder.buffer_frame(raw_frame)

        # Preview
        if self.show_preview and self.mode == CaptureMode.POLLING:
            self._show_frame(display_frame)

        # Callbacks
        if self.raw_frame_callback:
            try:
                self.raw_frame_callback(raw_frame, timestamp)
            except Exception as e:
                print(f"[CameraModule:{self.name}] raw_frame_callback error: {e}")

        if self.frame_callback and ml_frame is not None:
            try:
                self.frame_callback(display_frame, ml_frame, timestamp)
            except Exception as e:
                print(f"[CameraModule:{self.name}] frame_callback error: {e}")

    def _show_frame(self, display_frame: np.ndarray) -> None:
        """Show frame in preview window."""
        frame = display_frame.copy()

        if self.show_stats:
            stats = self.stats.get_stats()
            mode_name = "streaming" if self.mode == CaptureMode.STREAMING else "polling"
            text = f"FPS: {stats.avg_fps:.1f} | Lat: {stats.avg_latency_ms:.0f}ms | {mode_name}"
            cv2.putText(
                frame, text, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
            )

            if self._recorder and self._recorder.is_recording:
                cv2.circle(frame, (frame.shape[1] - 20, 20), 8, (0, 0, 255), -1)

        cv2.imshow(self.window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            self._stop_event.set()

    def _throttle(self, start_time: float) -> None:
        """Throttle to target FPS."""
        if self.target_period > 0:
            elapsed = time.time() - start_time
            sleep_time = self.target_period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
