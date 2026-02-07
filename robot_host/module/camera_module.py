# robot_host/modules/camera_module.py

import threading
import time
from typing import Callable, Optional, Tuple

import cv2
import numpy as np

from robot_host.module.camera_client import Esp32CamClient


FrameCallback = Callable[[np.ndarray, np.ndarray, float], None]
# signature: (display_frame, ml_frame, ts)


class CameraModule:
    """
    CameraModule:
    - Polls an ESP32-CAM via HTTP using Esp32CamClient
    - Optionally shows a live preview window
    - Optionally calls a user-provided callback with (display_frame, ml_frame, ts)
      so you can:
        * run ML models
        * publish to your internal event bus
        * log, etc.
    """

    def __init__(
        self,
        base_url: str,
        name: str = "front_cam",
        display_size: Tuple[int, int] = (320, 240),
        ml_size: Tuple[int, int] = (224, 224),
        blur_ksize: int = 0,
        fps: float = 5.0,
        show_preview: bool = False,
        frame_callback: Optional[FrameCallback] = None,
    ) -> None:
        """
        :param base_url: Base URL of ESP32-CAM, like "http://10.0.0.66"
        :param name:     Logical name of the camera for logging/events
        :param display_size: (w, h) for display frames
        :param ml_size:      (w, h) for ML frames
        :param blur_ksize:   Gaussian blur kernel size for display (0 = none)
        :param fps:          Target capture rate
        :param show_preview: If True, opens an OpenCV window
        :param frame_callback: Optional function called per frame:
                               cb(display_frame, ml_frame, ts)
        """
        self.name = name
        self.cam = Esp32CamClient(base_url)
        self.display_size = display_size
        self.ml_size = ml_size
        self.blur_ksize = blur_ksize
        self.target_period = 1.0 / fps if fps > 0 else 0.0
        self.show_preview = show_preview
        self.frame_callback = frame_callback

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ---------- Public control API ----------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name=f"CameraModule-{self.name}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.show_preview:
            try:
                cv2.destroyWindow(self._window_name)
            except Exception:
                pass
    
    def run_foreground(self) -> None:
        """
        Run the capture loop on the current (usually main) thread.

        Use this when show_preview=True on macOS, because OpenCV's GUI
        functions (namedWindow, imshow, waitKey) must be called from the
        main thread or they may crash.
        """
        self._stop_event.clear()
        self._run_loop()

    # ---------- Internal loop ----------

    @property
    def _window_name(self) -> str:
        return f"cam:{self.name}"

    def _run_loop(self) -> None:
        print(f"[CameraModule:{self.name}] Starting loop")
        if self.show_preview:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)

        while not self._stop_event.is_set():
            t0 = time.time()

            display_frame, ml_frame = self.cam.get_dual_frame(
                display_size=self.display_size,
                ml_size=self.ml_size,
                blur_ksize=self.blur_ksize,
                normalize=True,
                to_chw=True,
            )

            ts = time.time()

            if display_frame is None or ml_frame is None:
                print(f"[CameraModule:{self.name}] Failed to get frame")
            else:
                # Optional preview window
                if self.show_preview:
                    cv2.imshow(self._window_name, display_frame)
                    # Non-blocking key read
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print(f"[CameraModule:{self.name}] 'q' pressed, stopping")
                        self._stop_event.set()
                        break

                # Optional callback for ML / event bus integration
                if self.frame_callback is not None:
                    try:
                        self.frame_callback(display_frame, ml_frame, ts)
                    except Exception as e:
                        print(f"[CameraModule:{self.name}] frame_callback error: {e}")

            # FPS throttling
            if self.target_period > 0:
                elapsed = time.time() - t0
                sleep_s = self.target_period - elapsed
                if sleep_s > 0:
                    time.sleep(sleep_s)

        print(f"[CameraModule:{self.name}] Loop stopped")
