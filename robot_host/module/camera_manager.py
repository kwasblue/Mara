# robot_host/module/camera_manager.py
"""Multi-camera manager for coordinating multiple ESP32-CAMs."""

import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from robot_host.module.camera_stream import MjpegStreamClient, StreamFrame
from robot_host.module.camera_control import CameraControlClient, DeviceStatus, FrameSize
from robot_host.module.camera_stats import CameraStatistics
from robot_host.module.camera_recorder import FrameRecorder


class CameraState(Enum):
    """Camera connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class CameraInfo:
    """Information about a managed camera."""
    name: str
    url: str
    state: CameraState = CameraState.DISCONNECTED
    status: Optional[DeviceStatus] = None
    stats: Optional[CameraStatistics] = None
    last_frame: Optional[StreamFrame] = None
    last_error: Optional[str] = None
    enabled: bool = True


@dataclass
class MultiFrameResult:
    """Result from fetching frames from all cameras."""
    frames: Dict[str, Optional[np.ndarray]] = field(default_factory=dict)
    timestamp: float = 0.0
    success_count: int = 0
    total_count: int = 0

    @property
    def all_success(self) -> bool:
        return self.success_count == self.total_count


# Callback types
FrameCallback = Callable[[str, StreamFrame], None]  # (camera_name, frame)
StateCallback = Callable[[str, CameraState], None]  # (camera_name, state)
MotionCallback = Callable[[str], None]  # (camera_name)


class CameraManager:
    """
    Manages multiple ESP32-CAM devices.

    Features:
    - Add/remove cameras dynamically
    - Concurrent streaming from all cameras
    - Unified frame callback
    - Health monitoring
    - Coordinated recording
    """

    def __init__(
        self,
        health_check_interval: float = 30.0,
        auto_reconnect: bool = True,
    ):
        """
        :param health_check_interval: Seconds between health checks
        :param auto_reconnect: Automatically reconnect failed cameras
        """
        self.health_check_interval = health_check_interval
        self.auto_reconnect = auto_reconnect

        self._cameras: Dict[str, CameraInfo] = {}
        self._streams: Dict[str, MjpegStreamClient] = {}
        self._controls: Dict[str, CameraControlClient] = {}
        self._recorders: Dict[str, FrameRecorder] = {}
        self._lock = threading.Lock()

        self._running = False
        self._health_thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_frame: Optional[FrameCallback] = None
        self._on_state_change: Optional[StateCallback] = None
        self._on_motion: Optional[MotionCallback] = None

    # ---------- Camera Management ----------

    def add_camera(
        self,
        name: str,
        url: str,
        auth: Optional[Tuple[str, str]] = None,
        auto_start: bool = True,
    ) -> bool:
        """
        Add a camera to the manager.

        :param name: Unique name for the camera
        :param url: Base URL (e.g., "http://10.0.0.66")
        :param auth: Optional (username, password) for API
        :param auto_start: Start streaming immediately
        :return: True if added successfully
        """
        with self._lock:
            if name in self._cameras:
                print(f"[CameraManager] Camera '{name}' already exists")
                return False

            info = CameraInfo(name=name, url=url)
            self._cameras[name] = info
            self._controls[name] = CameraControlClient(url, auth=auth)

            # Create stream client
            stream = MjpegStreamClient(url)
            stream.set_on_frame(lambda f, n=name: self._handle_frame(n, f))
            stream.set_on_connect(lambda n=name: self._handle_connect(n))
            stream.set_on_disconnect(lambda e, n=name: self._handle_disconnect(n, e))
            self._streams[name] = stream

            print(f"[CameraManager] Added camera '{name}' at {url}")

            if auto_start and self._running:
                self._start_camera(name)

            return True

    def remove_camera(self, name: str) -> bool:
        """Remove a camera from the manager."""
        with self._lock:
            if name not in self._cameras:
                return False

            # Stop stream
            if name in self._streams:
                self._streams[name].stop()
                del self._streams[name]

            # Stop recorder
            if name in self._recorders:
                self._recorders[name].stop()
                del self._recorders[name]

            del self._cameras[name]
            del self._controls[name]

            print(f"[CameraManager] Removed camera '{name}'")
            return True

    def get_camera(self, name: str) -> Optional[CameraInfo]:
        """Get camera info by name."""
        return self._cameras.get(name)

    def list_cameras(self) -> List[CameraInfo]:
        """List all cameras."""
        return list(self._cameras.values())

    def get_camera_names(self) -> List[str]:
        """Get names of all cameras."""
        return list(self._cameras.keys())

    # ---------- Streaming Control ----------

    def start(self) -> None:
        """Start all cameras and health monitoring."""
        if self._running:
            return

        self._running = True

        # Start all enabled cameras
        with self._lock:
            for name in self._cameras:
                if self._cameras[name].enabled:
                    self._start_camera(name)

        # Start health check thread
        self._health_thread = threading.Thread(
            target=self._health_loop,
            name="CameraManager-Health",
            daemon=True,
        )
        self._health_thread.start()

        print("[CameraManager] Started")

    def stop(self) -> None:
        """Stop all cameras."""
        self._running = False

        # Stop all streams
        with self._lock:
            for stream in self._streams.values():
                stream.stop()

            # Stop all recorders
            for recorder in self._recorders.values():
                recorder.stop()

        if self._health_thread:
            self._health_thread.join(timeout=2.0)

        print("[CameraManager] Stopped")

    def enable_camera(self, name: str) -> bool:
        """Enable a camera (start streaming)."""
        if name not in self._cameras:
            return False

        self._cameras[name].enabled = True
        if self._running:
            self._start_camera(name)
        return True

    def disable_camera(self, name: str) -> bool:
        """Disable a camera (stop streaming)."""
        if name not in self._cameras:
            return False

        self._cameras[name].enabled = False
        if name in self._streams:
            self._streams[name].stop()
        return True

    def _start_camera(self, name: str) -> None:
        """Internal: start a camera stream."""
        if name in self._streams:
            self._cameras[name].state = CameraState.CONNECTING
            self._notify_state_change(name)
            self._streams[name].start()

    # ---------- Frame Access ----------

    def get_frame(self, name: str, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get latest frame from a specific camera."""
        if name not in self._streams:
            return None
        frame = self._streams[name].get_frame(timeout)
        return frame.data if frame else None

    def get_all_frames(self, timeout: float = 0.5) -> MultiFrameResult:
        """Get latest frame from all cameras."""
        result = MultiFrameResult(timestamp=time.time())

        for name in self._cameras:
            frame = self.get_frame(name, timeout)
            result.frames[name] = frame
            result.total_count += 1
            if frame is not None:
                result.success_count += 1

        return result

    # ---------- Camera Control ----------

    def get_control(self, name: str) -> Optional[CameraControlClient]:
        """Get control client for a camera."""
        return self._controls.get(name)

    def set_resolution_all(self, size: FrameSize) -> Dict[str, bool]:
        """Set resolution on all cameras."""
        results = {}
        for name, ctrl in self._controls.items():
            results[name] = ctrl.set_resolution(size)
        return results

    def set_quality_all(self, quality: int) -> Dict[str, bool]:
        """Set quality on all cameras."""
        results = {}
        for name, ctrl in self._controls.items():
            results[name] = ctrl.set_quality(quality)
        return results

    def toggle_flash_all(self) -> Dict[str, Optional[bool]]:
        """Toggle flash on all cameras."""
        results = {}
        for name, ctrl in self._controls.items():
            results[name] = ctrl.toggle_flash()
        return results

    # ---------- Recording ----------

    def start_recording(
        self,
        name: str,
        output_dir: str = "recordings",
        **kwargs,
    ) -> Optional[str]:
        """Start recording from a specific camera."""
        if name not in self._cameras:
            return None

        if name in self._recorders and self._recorders[name].is_recording:
            return None

        recorder = FrameRecorder(
            output_dir=output_dir,
            prefix=name,
            **kwargs,
        )
        self._recorders[name] = recorder
        return recorder.start(source=self._cameras[name].url)

    def stop_recording(self, name: str) -> bool:
        """Stop recording from a specific camera."""
        if name not in self._recorders:
            return False
        self._recorders[name].stop()
        return True

    def start_recording_all(self, output_dir: str = "recordings", **kwargs) -> Dict[str, str]:
        """Start recording from all cameras."""
        results = {}
        for name in self._cameras:
            path = self.start_recording(name, output_dir, **kwargs)
            if path:
                results[name] = path
        return results

    def stop_recording_all(self) -> None:
        """Stop all recordings."""
        for name in list(self._recorders.keys()):
            self.stop_recording(name)

    # ---------- Callbacks ----------

    def set_on_frame(self, callback: Optional[FrameCallback]) -> None:
        """Set callback for new frames (camera_name, frame)."""
        self._on_frame = callback

    def set_on_state_change(self, callback: Optional[StateCallback]) -> None:
        """Set callback for state changes (camera_name, state)."""
        self._on_state_change = callback

    def set_on_motion(self, callback: Optional[MotionCallback]) -> None:
        """Set callback for motion detection events."""
        self._on_motion = callback

    # ---------- Statistics ----------

    def get_stats(self, name: str) -> Optional[CameraStatistics]:
        """Get statistics for a camera."""
        if name in self._streams:
            return self._streams[name].stats.get_stats()
        return None

    def get_all_stats(self) -> Dict[str, CameraStatistics]:
        """Get statistics for all cameras."""
        return {name: self.get_stats(name) for name in self._cameras if self.get_stats(name)}

    def print_status(self) -> None:
        """Print status of all cameras."""
        print("\n=== Camera Manager Status ===")
        for name, info in self._cameras.items():
            stats = self.get_stats(name)
            status_str = f"  {name}: {info.state.value}"
            if stats:
                status_str += f" | FPS: {stats.avg_fps:.1f} | Latency: {stats.avg_latency_ms:.0f}ms"
            if info.last_error:
                status_str += f" | Error: {info.last_error}"
            print(status_str)
        print("=" * 30 + "\n")

    # ---------- Internal Handlers ----------

    def _handle_frame(self, name: str, frame: StreamFrame) -> None:
        """Handle incoming frame from a camera."""
        if name in self._cameras:
            self._cameras[name].last_frame = frame
            self._cameras[name].stats = self._streams[name].stats.get_stats()

        # Forward to recorder
        if name in self._recorders and self._recorders[name].is_recording:
            self._recorders[name].add_frame(frame.data, frame.timestamp)

        # User callback
        if self._on_frame:
            try:
                self._on_frame(name, frame)
            except Exception as e:
                print(f"[CameraManager] Frame callback error: {e}")

    def _handle_connect(self, name: str) -> None:
        """Handle camera connection."""
        if name in self._cameras:
            self._cameras[name].state = CameraState.CONNECTED
            self._cameras[name].last_error = None
            self._notify_state_change(name)
            print(f"[CameraManager] Camera '{name}' connected")

    def _handle_disconnect(self, name: str, error: str) -> None:
        """Handle camera disconnection."""
        if name in self._cameras:
            self._cameras[name].state = CameraState.DISCONNECTED
            self._cameras[name].last_error = error
            self._notify_state_change(name)
            print(f"[CameraManager] Camera '{name}' disconnected: {error}")

    def _notify_state_change(self, name: str) -> None:
        """Notify state change callback."""
        if self._on_state_change and name in self._cameras:
            try:
                self._on_state_change(name, self._cameras[name].state)
            except Exception:
                pass

    def _health_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            time.sleep(self.health_check_interval)

            if not self._running:
                break

            for name, ctrl in self._controls.items():
                if name not in self._cameras or not self._cameras[name].enabled:
                    continue

                try:
                    status = ctrl.get_status()
                    if status:
                        self._cameras[name].status = status

                        # Check for motion events
                        if status.motion_enabled and self._on_motion:
                            # Could check last_motion timestamp here
                            pass
                except Exception:
                    pass
