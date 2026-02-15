# robot_host/module/camera_stats.py
"""Frame statistics tracking for camera clients."""

import time
import threading
from dataclasses import dataclass, field
from typing import Deque, Optional
from collections import deque


@dataclass
class FrameStats:
    """Statistics for a single frame capture."""
    timestamp: float
    latency_ms: float
    size_bytes: int
    success: bool
    error: Optional[str] = None


@dataclass
class CameraStatistics:
    """Aggregated camera performance statistics."""
    total_frames: int = 0
    successful_frames: int = 0
    failed_frames: int = 0
    corrupt_frames: int = 0

    total_bytes: int = 0

    avg_fps: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0

    last_error: Optional[str] = None
    last_frame_time: float = 0.0
    uptime_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.successful_frames / self.total_frames

    @property
    def avg_frame_size_kb(self) -> float:
        if self.successful_frames == 0:
            return 0.0
        return (self.total_bytes / self.successful_frames) / 1024


class StatsTracker:
    """
    Tracks frame capture statistics over a sliding window.
    Thread-safe for use with camera modules.
    """

    def __init__(self, window_size: int = 100, fps_window_seconds: float = 5.0):
        """
        :param window_size: Number of frames to keep for statistics
        :param fps_window_seconds: Time window for FPS calculation
        """
        self.window_size = window_size
        self.fps_window_seconds = fps_window_seconds

        self._frames: Deque[FrameStats] = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._start_time = time.time()

        # Counters (never reset, for lifetime stats)
        self._total_frames = 0
        self._successful_frames = 0
        self._failed_frames = 0
        self._corrupt_frames = 0
        self._total_bytes = 0
        self._last_error: Optional[str] = None

    def record_frame(
        self,
        latency_ms: float,
        size_bytes: int,
        success: bool,
        error: Optional[str] = None,
        corrupt: bool = False,
    ) -> None:
        """Record a frame capture attempt."""
        now = time.time()
        stats = FrameStats(
            timestamp=now,
            latency_ms=latency_ms,
            size_bytes=size_bytes,
            success=success,
            error=error,
        )

        with self._lock:
            self._frames.append(stats)
            self._total_frames += 1

            if success:
                self._successful_frames += 1
                self._total_bytes += size_bytes
            else:
                self._failed_frames += 1
                if error:
                    self._last_error = error

            if corrupt:
                self._corrupt_frames += 1

    def record_success(self, latency_ms: float, size_bytes: int) -> None:
        """Convenience method for successful frame."""
        self.record_frame(latency_ms, size_bytes, success=True)

    def record_failure(self, error: str, latency_ms: float = 0.0) -> None:
        """Convenience method for failed frame."""
        self.record_frame(latency_ms, 0, success=False, error=error)

    def record_corrupt(self, latency_ms: float, size_bytes: int) -> None:
        """Convenience method for corrupt frame."""
        self.record_frame(latency_ms, size_bytes, success=False, error="corrupt", corrupt=True)

    def get_stats(self) -> CameraStatistics:
        """Get current aggregated statistics."""
        now = time.time()

        with self._lock:
            stats = CameraStatistics(
                total_frames=self._total_frames,
                successful_frames=self._successful_frames,
                failed_frames=self._failed_frames,
                corrupt_frames=self._corrupt_frames,
                total_bytes=self._total_bytes,
                last_error=self._last_error,
                uptime_seconds=now - self._start_time,
            )

            if not self._frames:
                return stats

            # Calculate FPS over recent window
            fps_cutoff = now - self.fps_window_seconds
            recent_frames = [f for f in self._frames if f.timestamp > fps_cutoff and f.success]

            if len(recent_frames) >= 2:
                time_span = recent_frames[-1].timestamp - recent_frames[0].timestamp
                if time_span > 0:
                    stats.avg_fps = (len(recent_frames) - 1) / time_span

            # Calculate latency stats from successful frames in window
            successful_in_window = [f for f in self._frames if f.success]
            if successful_in_window:
                latencies = [f.latency_ms for f in successful_in_window]
                stats.avg_latency_ms = sum(latencies) / len(latencies)
                stats.min_latency_ms = min(latencies)
                stats.max_latency_ms = max(latencies)
                stats.last_frame_time = successful_in_window[-1].timestamp

            return stats

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._frames.clear()
            self._start_time = time.time()
            self._total_frames = 0
            self._successful_frames = 0
            self._failed_frames = 0
            self._corrupt_frames = 0
            self._total_bytes = 0
            self._last_error = None

    def __str__(self) -> str:
        s = self.get_stats()
        return (
            f"Frames: {s.successful_frames}/{s.total_frames} "
            f"({s.success_rate:.1%}) | "
            f"FPS: {s.avg_fps:.1f} | "
            f"Latency: {s.avg_latency_ms:.0f}ms"
        )
