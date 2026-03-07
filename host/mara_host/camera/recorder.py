# mara_host/module/camera_recorder.py
"""Camera recording to disk."""

import os
import time
import threading
import json
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, asdict
from queue import Queue, Empty
from datetime import datetime

import cv2
import numpy as np


@dataclass
class RecordingMetadata:
    """Metadata for a recording session."""
    start_time: str
    end_time: Optional[str] = None
    frame_count: int = 0
    duration_seconds: float = 0.0
    avg_fps: float = 0.0
    resolution: Optional[tuple] = None
    codec: str = "MJPG"
    source: str = ""


class FrameRecorder:
    """
    Records frames to disk as video or image sequence.

    Supports:
    - Video recording (AVI/MP4)
    - Image sequence (JPEG/PNG)
    - Async recording with background thread
    - Metadata logging
    """

    def __init__(
        self,
        output_dir: str = "recordings",
        prefix: str = "cam",
        fps: float = 10.0,
        codec: str = "MJPG",
        format: str = "video",  # "video" or "images"
        image_format: str = "jpg",
        jpeg_quality: int = 90,
        max_duration_seconds: float = 0,  # 0 = unlimited
        max_frames: int = 0,  # 0 = unlimited
    ):
        """
        :param output_dir: Directory for recordings
        :param prefix: Filename prefix
        :param fps: Target FPS for video
        :param codec: Video codec (MJPG, XVID, mp4v, etc.)
        :param format: "video" for single video file, "images" for image sequence
        :param image_format: "jpg" or "png" for image sequence
        :param jpeg_quality: JPEG quality for images (0-100)
        :param max_duration_seconds: Max recording duration (0 = unlimited)
        :param max_frames: Max frames to record (0 = unlimited)
        """
        self.output_dir = Path(output_dir)
        self.prefix = prefix
        self.fps = fps
        self.codec = codec
        self.format = format
        self.image_format = image_format
        self.jpeg_quality = jpeg_quality
        self.max_duration = max_duration_seconds
        self.max_frames = max_frames

        self._recording = False
        self._frame_queue: Queue = Queue(maxsize=100)
        self._writer_thread: Optional[threading.Thread] = None
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._session_dir: Optional[Path] = None

        self._frame_count = 0
        self._start_time: Optional[float] = None
        self._resolution: Optional[tuple] = None

        # Callbacks
        self._on_frame_written: Optional[Callable[[int], None]] = None
        self._on_recording_stopped: Optional[Callable[[RecordingMetadata], None]] = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def duration(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def start(self, source: str = "") -> str:
        """
        Start recording.

        :param source: Source identifier for metadata
        :return: Path to recording output
        """
        if self._recording:
            return str(self._session_dir or self.output_dir)

        # Create session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"{self.prefix}_{timestamp}"

        if self.format == "images":
            self._session_dir = self.output_dir / session_name
            self._session_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(self._session_dir)
        else:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(self.output_dir / f"{session_name}.avi")
            self._session_dir = self.output_dir

        self._frame_count = 0
        self._start_time = time.time()
        self._resolution = None
        self._recording = True

        # Start writer thread
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            args=(output_path, source),
            name="FrameRecorder",
            daemon=True,
        )
        self._writer_thread.start()

        print(f"[Recorder] Recording started: {output_path}")
        return output_path

    def stop(self) -> Optional[RecordingMetadata]:
        """Stop recording and return metadata."""
        if not self._recording:
            return None

        self._recording = False

        # Signal writer to stop
        self._frame_queue.put(None)

        if self._writer_thread:
            self._writer_thread.join(timeout=5.0)

        return self._get_metadata()

    def add_frame(self, frame: np.ndarray, timestamp: Optional[float] = None) -> bool:
        """
        Add a frame to be recorded.

        :param frame: BGR image
        :param timestamp: Optional timestamp (for metadata)
        :return: True if frame was queued
        """
        if not self._recording:
            return False

        # Check limits
        if self.max_frames > 0 and self._frame_count >= self.max_frames:
            self.stop()
            return False

        if self.max_duration > 0 and self.duration >= self.max_duration:
            self.stop()
            return False

        try:
            self._frame_queue.put_nowait((frame.copy(), timestamp or time.time()))
            return True
        except Exception:
            return False

    def set_on_frame_written(self, callback: Callable[[int], None]) -> None:
        """Set callback for each frame written (receives frame count)."""
        self._on_frame_written = callback

    def set_on_recording_stopped(self, callback: Callable[[RecordingMetadata], None]) -> None:
        """Set callback for recording stopped."""
        self._on_recording_stopped = callback

    def _writer_loop(self, output_path: str, source: str) -> None:
        """Background writer loop."""
        timestamps = []

        try:
            while True:
                try:
                    item = self._frame_queue.get(timeout=1.0)
                except Empty:
                    if not self._recording:
                        break
                    continue

                if item is None:
                    break

                frame, ts = item
                timestamps.append(ts)

                # Initialize on first frame
                if self._resolution is None:
                    self._resolution = (frame.shape[1], frame.shape[0])
                    if self.format == "video":
                        fourcc = cv2.VideoWriter_fourcc(*self.codec)
                        self._video_writer = cv2.VideoWriter(
                            output_path,
                            fourcc,
                            self.fps,
                            self._resolution,
                        )

                # Write frame
                if self.format == "video" and self._video_writer:
                    self._video_writer.write(frame)
                else:
                    frame_path = Path(output_path) / f"frame_{self._frame_count:06d}.{self.image_format}"
                    if self.image_format == "jpg":
                        cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                    else:
                        cv2.imwrite(str(frame_path), frame)

                self._frame_count += 1

                if self._on_frame_written:
                    try:
                        self._on_frame_written(self._frame_count)
                    except Exception:
                        pass

        finally:
            if self._video_writer:
                self._video_writer.release()
                self._video_writer = None

            # Write metadata
            metadata = self._get_metadata(source)
            metadata_path = Path(output_path).parent / f"{Path(output_path).stem}_metadata.json"
            if self.format == "images":
                metadata_path = Path(output_path) / "metadata.json"

            with open(metadata_path, "w") as f:
                json.dump(asdict(metadata), f, indent=2)

            if self._on_recording_stopped:
                try:
                    self._on_recording_stopped(metadata)
                except Exception:
                    pass

            print(f"[Recorder] Recording stopped: {self._frame_count} frames")

    def _get_metadata(self, source: str = "") -> RecordingMetadata:
        """Generate recording metadata."""
        duration = self.duration
        avg_fps = self._frame_count / duration if duration > 0 else 0

        return RecordingMetadata(
            start_time=datetime.fromtimestamp(self._start_time or 0).isoformat(),
            end_time=datetime.now().isoformat(),
            frame_count=self._frame_count,
            duration_seconds=round(duration, 2),
            avg_fps=round(avg_fps, 2),
            resolution=self._resolution,
            codec=self.codec if self.format == "video" else self.image_format,
            source=source,
        )


class MotionTriggeredRecorder(FrameRecorder):
    """
    Records video triggered by motion events.

    Keeps a pre-buffer of frames and starts recording when triggered.
    """

    def __init__(
        self,
        pre_buffer_seconds: float = 2.0,
        post_buffer_seconds: float = 5.0,
        **kwargs,
    ):
        """
        :param pre_buffer_seconds: Seconds of video to keep before trigger
        :param post_buffer_seconds: Seconds to continue recording after trigger
        """
        super().__init__(**kwargs)
        self.pre_buffer_seconds = pre_buffer_seconds
        self.post_buffer_seconds = post_buffer_seconds

        self._pre_buffer: list = []
        self._pre_buffer_frames = int(pre_buffer_seconds * self.fps)
        self._trigger_time: Optional[float] = None
        self._auto_stop_time: Optional[float] = None

    def buffer_frame(self, frame: np.ndarray) -> None:
        """Add frame to pre-buffer (call continuously)."""
        self._pre_buffer.append((frame.copy(), time.time()))

        # Trim buffer
        while len(self._pre_buffer) > self._pre_buffer_frames:
            self._pre_buffer.pop(0)

        # Check auto-stop
        if self._auto_stop_time and time.time() >= self._auto_stop_time:
            self.stop()
            self._auto_stop_time = None

        # If recording, also add to recording queue
        if self._recording:
            self.add_frame(frame)

    def trigger(self, source: str = "motion") -> str:
        """
        Trigger recording start.

        :return: Recording path
        """
        if self._recording:
            # Extend recording time
            self._auto_stop_time = time.time() + self.post_buffer_seconds
            return str(self._session_dir or "")

        # Start recording
        path = self.start(source)
        self._trigger_time = time.time()
        self._auto_stop_time = time.time() + self.post_buffer_seconds

        # Add pre-buffer frames
        for frame, ts in self._pre_buffer:
            self.add_frame(frame, ts)

        return path
