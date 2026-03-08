# mara_host/services/camera/stream_service.py
"""
Camera streaming service.

Provides a high-level wrapper around MjpegStreamClient.
"""

from dataclasses import dataclass
from typing import Optional, Callable, Any
import time

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class CameraFrame:
    """A frame from the camera stream."""

    data: Any  # numpy array if available
    timestamp: float
    size_bytes: int
    sequence: int
    width: int = 0
    height: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if frame contains valid data."""
        return self.data is not None and self.size_bytes > 0


@dataclass
class StreamStats:
    """Camera stream statistics."""

    fps: float = 0.0
    bytes_per_second: float = 0.0
    frames_received: int = 0
    frames_dropped: int = 0
    decode_time_ms: float = 0.0
    connected: bool = False
    uptime_s: float = 0.0


class StreamService:
    """
    Service for camera stream management.

    Wraps MjpegStreamClient with additional conveniences
    for GUI/CLI integration.

    Example:
        stream = StreamService("http://10.0.0.60")

        # Set callbacks
        stream.on_frame(lambda f: display(f.data))
        stream.on_connect(lambda: print("Connected!"))

        # Start streaming
        stream.start()

        # Get frames
        frame = stream.get_frame()
        if frame and frame.is_valid:
            process(frame.data)

        # Get statistics
        stats = stream.get_stats()
        print(f"FPS: {stats.fps}")

        # Stop when done
        stream.stop()
    """

    def __init__(
        self,
        base_url: str,
        stream_port: int = 81,
        buffer_size: int = 3,
        timeout: float = 10.0,
    ):
        """
        Initialize stream service.

        Args:
            base_url: Base URL of ESP32-CAM (e.g., "http://10.0.0.60")
            stream_port: Port for MJPEG stream (default 81)
            buffer_size: Number of frames to buffer
            timeout: Connection timeout
        """
        self.base_url = base_url
        self.stream_port = stream_port
        self.buffer_size = buffer_size
        self.timeout = timeout

        self._client = None
        self._started = False
        self._start_time: float = 0.0

        # Callbacks
        self._frame_callbacks: list[Callable[[CameraFrame], None]] = []
        self._connect_callbacks: list[Callable[[], None]] = []
        self._disconnect_callbacks: list[Callable[[str], None]] = []

    def _ensure_client(self) -> None:
        """Create the underlying client if needed."""
        if self._client is not None:
            return

        try:
            from mara_host.camera.stream import MjpegStreamClient

            self._client = MjpegStreamClient(
                base_url=self.base_url,
                stream_port=self.stream_port,
                buffer_size=self.buffer_size,
                timeout=self.timeout,
            )

            # Wire up callbacks
            self._client.set_on_frame(self._on_frame)
            self._client.set_on_connect(self._on_connect)
            self._client.set_on_disconnect(self._on_disconnect)
        except ImportError as e:
            raise RuntimeError(
                f"Camera streaming requires opencv-python: {e}"
            ) from e

    def start(self) -> None:
        """Start the camera stream."""
        if self._started:
            return

        self._ensure_client()
        self._client.start()
        self._started = True
        self._start_time = time.time()

    def stop(self) -> None:
        """Stop the camera stream."""
        if self._client:
            self._client.stop()
        self._started = False

    def is_running(self) -> bool:
        """Check if stream is running."""
        if self._client:
            return self._client.is_running()
        return False

    def is_connected(self) -> bool:
        """Check if stream is connected."""
        if self._client:
            return self._client.is_connected()
        return False

    def get_frame(self, timeout: float = 1.0) -> Optional[CameraFrame]:
        """
        Get the most recent frame.

        Args:
            timeout: Max time to wait for a frame

        Returns:
            CameraFrame or None
        """
        if not self._client:
            return None

        stream_frame = self._client.get_frame(timeout)
        if stream_frame is None:
            return None

        # Get dimensions if available
        width, height = 0, 0
        if HAS_NUMPY and stream_frame.data is not None:
            height, width = stream_frame.data.shape[:2]

        return CameraFrame(
            data=stream_frame.data,
            timestamp=stream_frame.timestamp,
            size_bytes=stream_frame.size_bytes,
            sequence=stream_frame.sequence,
            width=width,
            height=height,
        )

    def get_frame_bgr(self, timeout: float = 1.0) -> Optional[Any]:
        """Get just the BGR image data."""
        frame = self.get_frame(timeout)
        return frame.data if frame else None

    def get_stats(self) -> StreamStats:
        """Get stream statistics."""
        if not self._client:
            return StreamStats()

        try:
            camera_stats = self._client.get_stats()
            return StreamStats(
                fps=camera_stats.fps,
                bytes_per_second=camera_stats.bytes_per_second,
                frames_received=camera_stats.frames_received,
                frames_dropped=camera_stats.frames_dropped,
                decode_time_ms=camera_stats.avg_decode_time_ms,
                connected=self._client.is_connected(),
                uptime_s=time.time() - self._start_time if self._started else 0.0,
            )
        except Exception:
            return StreamStats(
                connected=self._client.is_connected() if self._client else False,
                uptime_s=time.time() - self._start_time if self._started else 0.0,
            )

    # Callback registration

    def on_frame(self, callback: Callable[[CameraFrame], None]) -> None:
        """Register callback for new frames."""
        self._frame_callbacks.append(callback)

    def on_connect(self, callback: Callable[[], None]) -> None:
        """Register callback for connection established."""
        self._connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable[[str], None]) -> None:
        """Register callback for disconnection."""
        self._disconnect_callbacks.append(callback)

    # Internal handlers

    def _on_frame(self, stream_frame: Any) -> None:
        """Handle frame from underlying client."""
        width, height = 0, 0
        if HAS_NUMPY and stream_frame.data is not None:
            height, width = stream_frame.data.shape[:2]

        frame = CameraFrame(
            data=stream_frame.data,
            timestamp=stream_frame.timestamp,
            size_bytes=stream_frame.size_bytes,
            sequence=stream_frame.sequence,
            width=width,
            height=height,
        )

        for cb in self._frame_callbacks:
            try:
                cb(frame)
            except Exception:
                pass

    def _on_connect(self) -> None:
        """Handle connection established."""
        for cb in self._connect_callbacks:
            try:
                cb()
            except Exception:
                pass

    def _on_disconnect(self, error: str) -> None:
        """Handle disconnection."""
        for cb in self._disconnect_callbacks:
            try:
                cb(error)
            except Exception:
                pass

    # Context manager

    def __enter__(self) -> "StreamService":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
