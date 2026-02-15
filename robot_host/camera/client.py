# robot_host/module/camera_client.py
"""
Enhanced ESP32-CAM client with connection resilience, statistics, and control.
"""

import time
from typing import Optional, Iterator, Tuple, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future

import requests
import numpy as np
import cv2

from robot_host.vision.ml_preprocess import preprocess_for_ml
from robot_host.camera.stats import StatsTracker, CameraStatistics
from robot_host.camera.control import (
    CameraControlClient,
    CameraConfig,
    MotionConfig,
    DeviceStatus,
    FrameSize,
)


@dataclass
class FrameResult:
    """Result of a frame fetch operation."""
    frame: Optional[np.ndarray]
    timestamp: float
    latency_ms: float
    size_bytes: int
    success: bool
    error: Optional[str] = None


class Esp32CamClient:
    """
    Enhanced client for ESP32-CAM with:
    - Connection resilience (retry, backoff)
    - Frame statistics tracking
    - Camera control API integration
    - Configurable timeouts
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 3.0,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        auth: Optional[Tuple[str, str]] = None,
    ):
        """
        :param base_url: Base URL of the ESP32-CAM, e.g. "http://10.0.0.66"
        :param timeout: HTTP timeout in seconds for each request
        :param max_retries: Maximum retry attempts on failure
        :param retry_delay: Delay between retries (doubles each attempt)
        :param auth: Optional (username, password) for protected endpoints
        """
        self.base_url = base_url.rstrip("/")

        if base_url.endswith("/jpg"):
            self.snapshot_url = base_url
        else:
            self.snapshot_url = self.base_url + "/jpg"

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.session = requests.Session()
        if auth:
            self.session.auth = auth

        # Statistics tracking
        self.stats = StatsTracker()

        # Control client (lazy initialized)
        self._control: Optional[CameraControlClient] = None
        self._auth = auth

        # Connection state
        self._consecutive_failures = 0
        self._last_success_time: Optional[float] = None
        self._is_healthy = True

        # Callbacks
        self._on_frame: Optional[Callable[[FrameResult], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # Async decode support (ThreadPoolExecutor for JPEG decoding)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._pending_decode: Optional[Future] = None

    @property
    def control(self) -> CameraControlClient:
        """Get the camera control client."""
        if self._control is None:
            self._control = CameraControlClient(self.base_url, auth=self._auth)
        return self._control

    @property
    def is_healthy(self) -> bool:
        """Check if camera is responding."""
        return self._is_healthy

    def get_stats(self) -> CameraStatistics:
        """Get current frame statistics."""
        return self.stats.get_stats()

    # ---------- Callbacks ----------

    def set_on_frame(self, callback: Optional[Callable[[FrameResult], None]]) -> None:
        """Set callback for each frame fetch attempt."""
        self._on_frame = callback

    def set_on_error(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set callback for errors."""
        self._on_error = callback

    # ---------- Async decode support ----------

    def enable_async_decode(self, max_workers: int = 2) -> None:
        """
        Enable async JPEG decoding using a thread pool.

        This reduces blocking in the main loop by offloading JPEG decode
        to a background thread. Python's GIL allows this since cv2.imdecode
        releases the GIL during the actual decode operation.

        :param max_workers: Number of decoder threads (1-2 is usually enough)
        """
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def disable_async_decode(self) -> None:
        """Disable async JPEG decoding."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
            self._pending_decode = None

    def _decode_jpeg(self, jpeg_bytes: bytes) -> Tuple[Optional[np.ndarray], float]:
        """
        Decode JPEG bytes to BGR array.

        :return: (frame, decode_time_ms)
        """
        t0 = time.time()
        jpg = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
        decode_ms = (time.time() - t0) * 1000
        return frame, decode_ms

    # ---------- Core frame fetch ----------

    def _fetch_raw_bgr(self, retry: bool = True) -> FrameResult:
        """
        Fetch and decode a single JPEG as BGR image.

        :param retry: Whether to retry on failure
        :return: FrameResult with frame data or error
        """
        attempts = self.max_retries if retry else 1
        delay = self.retry_delay
        last_error = ""

        for attempt in range(attempts):
            t0 = time.time()

            try:
                resp = self.session.get(self.snapshot_url, timeout=self.timeout)
                resp.raise_for_status()

                fetch_ms = (time.time() - t0) * 1000
                size_bytes = len(resp.content)

                # Decode JPEG (with timing)
                if self._executor is not None:
                    # Async decode - submit to thread pool
                    future = self._executor.submit(self._decode_jpeg, resp.content)
                    frame, decode_ms = future.result()  # Wait for result
                else:
                    # Sync decode
                    frame, decode_ms = self._decode_jpeg(resp.content)

                # Track decode time
                self.stats.record_decode_time(decode_ms)
                latency_ms = fetch_ms + decode_ms

                if frame is None:
                    self.stats.record_corrupt(latency_ms, size_bytes)
                    last_error = "Failed to decode JPEG"
                    continue

                # Success
                self.stats.record_success(latency_ms, size_bytes)
                self._consecutive_failures = 0
                self._last_success_time = time.time()
                self._is_healthy = True

                result = FrameResult(
                    frame=frame,
                    timestamp=time.time(),
                    latency_ms=latency_ms,
                    size_bytes=size_bytes,
                    success=True,
                )

                if self._on_frame:
                    self._on_frame(result)

                return result

            except requests.Timeout:
                latency_ms = (time.time() - t0) * 1000
                last_error = "timeout"
                self.stats.record_failure(last_error, latency_ms)

            except requests.ConnectionError as e:
                latency_ms = (time.time() - t0) * 1000
                last_error = f"connection error: {e}"
                self.stats.record_failure("connection_error", latency_ms)

            except Exception as e:
                latency_ms = (time.time() - t0) * 1000
                last_error = str(e)
                self.stats.record_failure(last_error, latency_ms)

            # Retry with backoff
            if attempt < attempts - 1:
                time.sleep(delay)
                delay *= 2

        # All attempts failed
        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self._is_healthy = False

        if self._on_error:
            self._on_error(last_error)

        return FrameResult(
            frame=None,
            timestamp=time.time(),
            latency_ms=0,
            size_bytes=0,
            success=False,
            error=last_error,
        )

    # ---------- Public APIs ----------

    def get_frame(
        self,
        resize_to: Optional[Tuple[int, int]] = None,
        blur_ksize: int = 0,
        retry: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Get a display-ready BGR frame.

        :param resize_to: (width, height) to resize to (e.g. (320, 240))
        :param blur_ksize: Optional Gaussian blur kernel size (0 = no blur)
        :param retry: Whether to retry on failure
        :return: BGR image or None on failure
        """
        result = self._fetch_raw_bgr(retry=retry)
        if not result.success or result.frame is None:
            return None

        frame = result.frame

        if resize_to is not None:
            frame = cv2.resize(frame, resize_to, interpolation=cv2.INTER_AREA)

        if blur_ksize and blur_ksize > 1:
            if blur_ksize % 2 == 0:
                blur_ksize += 1
            frame = cv2.GaussianBlur(frame, (blur_ksize, blur_ksize), 0)

        return frame

    def get_frame_with_info(
        self,
        resize_to: Optional[Tuple[int, int]] = None,
        blur_ksize: int = 0,
    ) -> FrameResult:
        """
        Get frame with metadata (latency, size, etc.).

        :return: FrameResult object
        """
        result = self._fetch_raw_bgr()

        if result.success and result.frame is not None:
            if resize_to is not None:
                result.frame = cv2.resize(result.frame, resize_to, interpolation=cv2.INTER_AREA)

            if blur_ksize and blur_ksize > 1:
                if blur_ksize % 2 == 0:
                    blur_ksize += 1
                result.frame = cv2.GaussianBlur(result.frame, (blur_ksize, blur_ksize), 0)

        return result

    def get_frame_for_ml(
        self,
        target_size: Tuple[int, int] = (224, 224),
        normalize: bool = True,
        to_chw: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Get an ML-ready frame (float32, normalized).

        :return: np.ndarray with shape (C, H, W) if to_chw=True,
                 else (H, W, C), or None on failure.
        """
        result = self._fetch_raw_bgr()
        if not result.success or result.frame is None:
            return None

        return preprocess_for_ml(
            result.frame,
            target_size=target_size,
            normalize=normalize,
            to_chw=to_chw,
        )

    def get_dual_frame(
        self,
        display_size: Tuple[int, int] = (320, 240),
        ml_size: Tuple[int, int] = (224, 224),
        blur_ksize: int = 0,
        normalize: bool = True,
        to_chw: bool = True,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Get both display and ML-ready frames from a single capture.

        :return: (display_frame, ml_frame) – either can be None if fetch fails.
        """
        result = self._fetch_raw_bgr()
        if not result.success or result.frame is None:
            return None, None

        frame = result.frame

        # Display version
        display_frame = frame.copy()
        if display_size is not None:
            display_frame = cv2.resize(display_frame, display_size, interpolation=cv2.INTER_AREA)
        if blur_ksize and blur_ksize > 1:
            if blur_ksize % 2 == 0:
                blur_ksize += 1
            display_frame = cv2.GaussianBlur(display_frame, (blur_ksize, blur_ksize), 0)

        # ML version
        ml_frame = preprocess_for_ml(
            frame,
            target_size=ml_size,
            normalize=normalize,
            to_chw=to_chw,
        )

        return display_frame, ml_frame

    # ---------- Camera Control Shortcuts ----------

    def get_status(self) -> Optional[DeviceStatus]:
        """Get camera device status."""
        return self.control.get_status()

    def set_resolution(self, size: FrameSize) -> bool:
        """Set camera resolution."""
        return self.control.set_resolution(size)

    def set_quality(self, quality: int) -> bool:
        """Set JPEG quality (0-63, lower = better)."""
        return self.control.set_quality(quality)

    def toggle_flash(self) -> Optional[bool]:
        """Toggle flash LED."""
        return self.control.toggle_flash()

    def set_flash(self, on: bool) -> bool:
        """Set flash to specific state."""
        return self.control.set_flash(on)

    def get_camera_config(self) -> Optional[CameraConfig]:
        """Get camera configuration."""
        return self.control.get_camera_config()

    def enable_motion_detection(self, sensitivity: int = 30) -> bool:
        """Enable motion detection."""
        return self.control.enable_motion_detection(sensitivity)

    def disable_motion_detection(self) -> bool:
        """Disable motion detection."""
        return self.control.disable_motion_detection()

    # ---------- Convenience methods ----------

    def iter_frames(
        self,
        delay: float = 0.0,
        max_frames: Optional[int] = None,
    ) -> Iterator[np.ndarray]:
        """
        Generator of display-ready frames.

        :param delay: Minimum delay between frames
        :param max_frames: Maximum frames to yield (None = infinite)
        """
        count = 0
        while max_frames is None or count < max_frames:
            frame = self.get_frame()
            if frame is not None:
                count += 1
                yield frame
            if delay > 0:
                time.sleep(delay)

    def test_preview(
        self,
        window_name: str = "ESP32-CAM",
        delay: float = 0.0,
        show_stats: bool = True,
    ) -> None:
        """
        Preview frames with optional stats overlay.

        :param window_name: OpenCV window name
        :param delay: Delay between frames
        :param show_stats: Show FPS/latency overlay
        """
        print(f"[Esp32CamClient] Starting preview from {self.snapshot_url} (press 'q' to quit)")

        for frame in self.iter_frames(delay=delay):
            if show_stats:
                stats = self.stats.get_stats()
                text = f"FPS: {stats.avg_fps:.1f} | Lat: {stats.avg_latency_ms:.0f}ms"
                cv2.putText(
                    frame, text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                )

            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()
        print(f"\n[Esp32CamClient] Final stats: {self.stats}")

    def test_connection(self) -> bool:
        """Test camera connection."""
        status = self.control.get_status()
        if status:
            print(f"[Esp32CamClient] Connected to {status.hostname} ({status.ip})")
            print(f"  RSSI: {status.rssi} dBm")
            print(f"  Free heap: {status.free_heap // 1024} KB")
            print(f"  Uptime: {status.uptime_seconds}s")
            return True
        else:
            print("[Esp32CamClient] Connection failed")
            return False

    def close(self) -> None:
        """Clean up resources (executor, session)."""
        self.disable_async_decode()
        self.session.close()

    def __enter__(self) -> "Esp32CamClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
