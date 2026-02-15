# robot_host/module/camera_stream.py
"""MJPEG stream client for ESP32-CAM."""

import threading
import time
from typing import Optional, Callable, Tuple
from collections import deque
from dataclasses import dataclass
import requests
import numpy as np
import cv2

from robot_host.module.camera_stats import StatsTracker
from robot_host.module.ml_preprocess import preprocess_for_ml


@dataclass
class StreamFrame:
    """A frame from the MJPEG stream."""
    data: np.ndarray          # BGR image
    timestamp: float          # Capture time
    size_bytes: int           # Original JPEG size
    sequence: int             # Frame sequence number


class MjpegStreamClient:
    """
    MJPEG stream client for ESP32-CAM.

    Connects to the /stream endpoint and continuously receives frames.
    Much more efficient than polling /jpg for each frame.

    Features:
    - Background thread for continuous streaming
    - Frame buffer to handle network jitter
    - Automatic reconnection on failure
    - Frame statistics tracking
    """

    BOUNDARY_MARKER = b"--123456789000000000000987654321"

    def __init__(
        self,
        base_url: str,
        buffer_size: int = 3,
        timeout: float = 10.0,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
        stream_port: int = 81,
    ):
        """
        :param base_url: Base URL of ESP32-CAM, e.g. "http://10.0.0.66"
        :param buffer_size: Number of frames to buffer
        :param timeout: HTTP connection timeout
        :param reconnect_delay: Initial delay between reconnection attempts
        :param max_reconnect_delay: Maximum reconnection delay (exponential backoff)
        :param stream_port: Port for MJPEG stream (default 81, separate from main server)
        """
        self.base_url = base_url.rstrip("/")
        # Build stream URL with separate port
        # Parse host from base_url and use stream_port
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        self.stream_url = f"{parsed.scheme}://{parsed.hostname}:{stream_port}/stream"
        self.buffer_size = buffer_size
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay

        self._frame_buffer: deque = deque(maxlen=buffer_size)
        self._buffer_lock = threading.Lock()
        self._frame_event = threading.Event()

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected = False
        self._sequence = 0

        self.stats = StatsTracker()

        # Callbacks
        self._on_frame: Optional[Callable[[StreamFrame], None]] = None
        self._on_connect: Optional[Callable[[], None]] = None
        self._on_disconnect: Optional[Callable[[str], None]] = None

    # ---------- Public API ----------

    def start(self) -> None:
        """Start the stream in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._stream_loop,
            name="MjpegStreamClient",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the stream."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._connected = False

    def is_connected(self) -> bool:
        """Check if stream is connected."""
        return self._connected

    def is_running(self) -> bool:
        """Check if stream thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def get_frame(self, timeout: float = 1.0) -> Optional[StreamFrame]:
        """
        Get the most recent frame from the buffer.

        :param timeout: Max time to wait for a frame
        :return: StreamFrame or None if no frame available
        """
        # Wait for frame if buffer empty
        if not self._frame_buffer:
            self._frame_event.wait(timeout)
            self._frame_event.clear()

        with self._buffer_lock:
            if self._frame_buffer:
                return self._frame_buffer[-1]  # Most recent
            return None

    def get_frame_bgr(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get just the BGR image data."""
        frame = self.get_frame(timeout)
        return frame.data if frame else None

    def get_dual_frame(
        self,
        display_size: Tuple[int, int] = (320, 240),
        ml_size: Tuple[int, int] = (224, 224),
        blur_ksize: int = 0,
        timeout: float = 1.0,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Get both display and ML-ready frames.

        :return: (display_frame, ml_frame) tuple
        """
        frame = self.get_frame(timeout)
        if frame is None:
            return None, None

        # Display version
        display = frame.data.copy()
        if display_size:
            display = cv2.resize(display, display_size, interpolation=cv2.INTER_AREA)
        if blur_ksize and blur_ksize > 1:
            if blur_ksize % 2 == 0:
                blur_ksize += 1
            display = cv2.GaussianBlur(display, (blur_ksize, blur_ksize), 0)

        # ML version
        ml = preprocess_for_ml(
            frame.data,
            target_size=ml_size,
            normalize=True,
            to_chw=True,
        )

        return display, ml

    def set_on_frame(self, callback: Optional[Callable[[StreamFrame], None]]) -> None:
        """Set callback for each new frame."""
        self._on_frame = callback

    def set_on_connect(self, callback: Optional[Callable[[], None]]) -> None:
        """Set callback for connection established."""
        self._on_connect = callback

    def set_on_disconnect(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set callback for disconnection (receives error message)."""
        self._on_disconnect = callback

    # ---------- Internal ----------

    def _stream_loop(self) -> None:
        """Main streaming loop with reconnection."""
        current_delay = self.reconnect_delay

        while not self._stop_event.is_set():
            try:
                self._connect_and_stream()
                current_delay = self.reconnect_delay  # Reset on success
            except Exception as e:
                error_msg = str(e)
                print(f"[MjpegStream] Connection error: {error_msg}")

                self._connected = False
                if self._on_disconnect:
                    try:
                        self._on_disconnect(error_msg)
                    except Exception:
                        pass

                # Exponential backoff
                if not self._stop_event.is_set():
                    print(f"[MjpegStream] Reconnecting in {current_delay:.1f}s...")
                    self._stop_event.wait(current_delay)
                    current_delay = min(current_delay * 2, self.max_reconnect_delay)

    def _connect_and_stream(self) -> None:
        """Connect to stream and process frames."""
        print(f"[MjpegStream] Connecting to {self.stream_url}")

        with requests.get(
            self.stream_url,
            stream=True,
            timeout=self.timeout,
        ) as response:
            response.raise_for_status()

            self._connected = True
            print("[MjpegStream] Connected")

            if self._on_connect:
                try:
                    self._on_connect()
                except Exception:
                    pass

            self._process_stream(response)

    def _process_stream(self, response: requests.Response) -> None:
        """Process MJPEG stream data."""
        buffer = b""
        content_length = 0
        reading_image = False

        for chunk in response.iter_content(chunk_size=4096):
            if self._stop_event.is_set():
                break

            buffer += chunk

            while True:
                if not reading_image:
                    # Look for boundary
                    boundary_pos = buffer.find(self.BOUNDARY_MARKER)
                    if boundary_pos == -1:
                        # Keep last part in case boundary is split
                        if len(buffer) > len(self.BOUNDARY_MARKER):
                            buffer = buffer[-(len(self.BOUNDARY_MARKER)):]
                        break

                    # Find headers after boundary
                    header_start = boundary_pos + len(self.BOUNDARY_MARKER)
                    header_end = buffer.find(b"\r\n\r\n", header_start)

                    if header_end == -1:
                        break  # Need more data

                    # Parse Content-Length
                    headers = buffer[header_start:header_end].decode("utf-8", errors="ignore")
                    for line in headers.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            content_length = int(line.split(":")[1].strip())
                            break

                    # Start reading image data
                    buffer = buffer[header_end + 4:]
                    reading_image = True

                if reading_image:
                    if len(buffer) >= content_length:
                        # Extract JPEG data
                        jpeg_data = buffer[:content_length]
                        buffer = buffer[content_length:]
                        reading_image = False

                        # Process frame
                        self._process_frame(jpeg_data)
                    else:
                        break  # Need more data

    def _process_frame(self, jpeg_data: bytes) -> None:
        """Decode and buffer a frame."""
        t0 = time.time()

        # Decode JPEG
        jpg_array = np.frombuffer(jpeg_data, dtype=np.uint8)
        frame_bgr = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

        latency_ms = (time.time() - t0) * 1000

        if frame_bgr is None:
            self.stats.record_corrupt(latency_ms, len(jpeg_data))
            return

        self._sequence += 1
        stream_frame = StreamFrame(
            data=frame_bgr,
            timestamp=time.time(),
            size_bytes=len(jpeg_data),
            sequence=self._sequence,
        )

        # Add to buffer
        with self._buffer_lock:
            self._frame_buffer.append(stream_frame)

        self._frame_event.set()
        self.stats.record_success(latency_ms, len(jpeg_data))

        # Callback
        if self._on_frame:
            try:
                self._on_frame(stream_frame)
            except Exception as e:
                print(f"[MjpegStream] Frame callback error: {e}")
