# robot_host/module/camera_async.py
"""Async camera client using aiohttp."""

import asyncio
import time
from typing import Optional, Tuple, AsyncIterator
from dataclasses import dataclass

import aiohttp
import numpy as np
import cv2

from robot_host.camera.stats import StatsTracker
from robot_host.vision.ml_preprocess import preprocess_for_ml


@dataclass
class AsyncFrame:
    """An async-fetched frame."""
    data: np.ndarray
    timestamp: float
    size_bytes: int
    latency_ms: float


class AsyncCameraClient:
    """
    Async camera client using aiohttp.

    For use in asyncio-based applications. Provides non-blocking
    frame fetching with connection pooling.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 3.0,
        max_connections: int = 2,
    ):
        """
        :param base_url: Base URL of ESP32-CAM
        :param timeout: Request timeout in seconds
        :param max_connections: Max concurrent connections
        """
        self.base_url = base_url.rstrip("/")
        self.snapshot_url = f"{self.base_url}/jpg"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_connections = max_connections

        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self.stats = StatsTracker()

    async def __aenter__(self) -> "AsyncCameraClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def connect(self) -> None:
        """Initialize the aiohttp session."""
        if self._session is None:
            self._connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections,
            )
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self.timeout,
            )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
        if self._connector:
            await self._connector.close()
            self._connector = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is initialized."""
        if self._session is None:
            await self.connect()
        return self._session  # type: ignore

    async def fetch_frame(self) -> Optional[AsyncFrame]:
        """
        Fetch a single frame asynchronously.

        :return: AsyncFrame or None on failure
        """
        session = await self._ensure_session()
        t0 = time.time()

        try:
            async with session.get(self.snapshot_url) as response:
                if response.status != 200:
                    self.stats.record_failure(f"HTTP {response.status}")
                    return None

                jpeg_data = await response.read()
                latency_ms = (time.time() - t0) * 1000

                # Decode JPEG
                jpg_array = np.frombuffer(jpeg_data, dtype=np.uint8)
                frame = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

                if frame is None:
                    self.stats.record_corrupt(latency_ms, len(jpeg_data))
                    return None

                self.stats.record_success(latency_ms, len(jpeg_data))

                return AsyncFrame(
                    data=frame,
                    timestamp=time.time(),
                    size_bytes=len(jpeg_data),
                    latency_ms=latency_ms,
                )

        except asyncio.TimeoutError:
            self.stats.record_failure("timeout", (time.time() - t0) * 1000)
            return None
        except Exception as e:
            self.stats.record_failure(str(e), (time.time() - t0) * 1000)
            return None

    async def fetch_frame_bgr(self) -> Optional[np.ndarray]:
        """Fetch just the BGR image."""
        frame = await self.fetch_frame()
        return frame.data if frame else None

    async def fetch_dual_frame(
        self,
        display_size: Tuple[int, int] = (320, 240),
        ml_size: Tuple[int, int] = (224, 224),
        blur_ksize: int = 0,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Fetch both display and ML-ready frames.

        :return: (display_frame, ml_frame) tuple
        """
        frame = await self.fetch_frame()
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

    async def iter_frames(
        self,
        target_fps: float = 10.0,
        max_frames: Optional[int] = None,
    ) -> AsyncIterator[AsyncFrame]:
        """
        Async generator for continuous frame fetching.

        :param target_fps: Target frames per second
        :param max_frames: Maximum frames to yield (None = infinite)
        """
        frame_period = 1.0 / target_fps if target_fps > 0 else 0
        frame_count = 0

        while max_frames is None or frame_count < max_frames:
            t0 = time.time()

            frame = await self.fetch_frame()
            if frame is not None:
                frame_count += 1
                yield frame

            # FPS throttling
            if frame_period > 0:
                elapsed = time.time() - t0
                sleep_time = frame_period - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)


class AsyncMjpegClient:
    """
    Async MJPEG stream client.

    Connects to /stream endpoint and yields frames asynchronously.
    """

    BOUNDARY = b"--123456789000000000000987654321"

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.stream_url = f"{self.base_url}/stream"
        self.timeout = aiohttp.ClientTimeout(total=timeout, sock_read=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self.stats = StatsTracker()

    async def __aenter__(self) -> "AsyncMjpegClient":
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.close()

    async def stream_frames(self) -> AsyncIterator[AsyncFrame]:
        """
        Async generator that yields frames from the MJPEG stream.

        Usage:
            async with AsyncMjpegClient("http://10.0.0.66") as client:
                async for frame in client.stream_frames():
                    process(frame.data)
        """
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

        async with self._session.get(self.stream_url) as response:
            if response.status != 200:
                raise ConnectionError(f"Stream returned {response.status}")

            buffer = b""
            content_length = 0
            reading_image = False
            sequence = 0

            async for chunk in response.content.iter_any():
                buffer += chunk

                while True:
                    if not reading_image:
                        # Find boundary
                        pos = buffer.find(self.BOUNDARY)
                        if pos == -1:
                            if len(buffer) > len(self.BOUNDARY):
                                buffer = buffer[-len(self.BOUNDARY):]
                            break

                        # Find headers
                        header_start = pos + len(self.BOUNDARY)
                        header_end = buffer.find(b"\r\n\r\n", header_start)
                        if header_end == -1:
                            break

                        # Parse Content-Length
                        headers = buffer[header_start:header_end].decode("utf-8", errors="ignore")
                        for line in headers.split("\r\n"):
                            if line.lower().startswith("content-length:"):
                                content_length = int(line.split(":")[1].strip())
                                break

                        buffer = buffer[header_end + 4:]
                        reading_image = True

                    if reading_image:
                        if len(buffer) >= content_length:
                            jpeg_data = buffer[:content_length]
                            buffer = buffer[content_length:]
                            reading_image = False

                            # Decode
                            t0 = time.time()
                            jpg_array = np.frombuffer(jpeg_data, dtype=np.uint8)
                            frame_bgr = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)
                            latency_ms = (time.time() - t0) * 1000

                            if frame_bgr is not None:
                                sequence += 1
                                self.stats.record_success(latency_ms, len(jpeg_data))
                                yield AsyncFrame(
                                    data=frame_bgr,
                                    timestamp=time.time(),
                                    size_bytes=len(jpeg_data),
                                    latency_ms=latency_ms,
                                )
                            else:
                                self.stats.record_corrupt(latency_ms, len(jpeg_data))
                        else:
                            break
