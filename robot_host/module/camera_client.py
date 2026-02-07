# camera_client.py
import time
from typing import Optional, Iterator, Tuple

import requests
import numpy as np
import cv2

from robot_host.module.ml_preprocess import preprocess_for_ml


class Esp32CamClient:
    """
    Simple client for an ESP32-CAM that exposes a JPEG snapshot endpoint,
    e.g. http://10.0.0.66/jpg
    """

    def __init__(self, base_url: str, timeout: float = 3.0):
        """
        :param base_url: Base URL of the ESP32-CAM, e.g. "http://10.0.0.66"
        :param timeout:  HTTP timeout in seconds for each request.
        """
        if base_url.endswith("/jpg"):
            self.snapshot_url = base_url
        else:
            self.snapshot_url = base_url.rstrip("/") + "/jpg"

        self.timeout = timeout
        self.session = requests.Session()

    # -------- Core frame fetch --------

    def _fetch_raw_bgr(self) -> Optional[np.ndarray]:
        """Internal: fetch and decode a single JPEG as BGR image."""
        try:
            resp = self.session.get(self.snapshot_url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            print(f"[Esp32CamClient] Error fetching frame: {e}")
            return None

        jpg = np.frombuffer(resp.content, dtype=np.uint8)
        frame = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
        if frame is None:
            print("[Esp32CamClient] Failed to decode JPEG")
            return None
        return frame

    # -------- Public APIs --------

    def get_frame(
        self,
        resize_to: Optional[Tuple[int, int]] = None,
        blur_ksize: int = 0,
    ) -> Optional[np.ndarray]:
        """
        Get a display-ready BGR frame.

        :param resize_to: (width, height) to resize to (e.g. (320, 240)).
                          If None, keep original size.
        :param blur_ksize: Optional Gaussian blur kernel size (0 = no blur).
        """
        frame = self._fetch_raw_bgr()
        if frame is None:
            return None

        # Resize for display if requested
        if resize_to is not None:
            frame = cv2.resize(frame, resize_to, interpolation=cv2.INTER_AREA)

        # Light blur to reduce noise if requested
        if blur_ksize and blur_ksize > 1:
            if blur_ksize % 2 == 0:
                blur_ksize += 1  # must be odd
            frame = cv2.GaussianBlur(frame, (blur_ksize, blur_ksize), 0)

        return frame

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
        frame = self._fetch_raw_bgr()
        if frame is None:
            return None

        return preprocess_for_ml(
            frame,
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
        Get both:
          - display_frame: BGR uint8, optionally resized/blurred
          - ml_frame:      float32 tensor, normalized for ML

        :return: (display_frame, ml_frame) – either can be None if fetch fails.
        """
        frame = self._fetch_raw_bgr()
        if frame is None:
            return None, None

        # 1) Display version
        display_frame = frame.copy()
        if display_size is not None:
            display_frame = cv2.resize(display_frame, display_size, interpolation=cv2.INTER_AREA)
        if blur_ksize and blur_ksize > 1:
            if blur_ksize % 2 == 0:
                blur_ksize += 1
            display_frame = cv2.GaussianBlur(display_frame, (blur_ksize, blur_ksize), 0)

        # 2) ML version
        ml_frame = preprocess_for_ml(
            frame,
            target_size=ml_size,
            normalize=normalize,
            to_chw=to_chw,
        )

        return display_frame, ml_frame

    # -------- Convenience preview --------

    def iter_frames(self, delay: float = 0.0) -> Iterator[np.ndarray]:
        """
        Simple generator of display-ready frames (no ML).
        """
        while True:
            frame = self.get_frame()
            if frame is not None:
                yield frame
            if delay > 0:
                time.sleep(delay)

    def test_preview(self, window_name: str = "ESP32-CAM", delay: float = 0.0):
        """
        Preview display frames (press 'q' to quit).
        """
        print(f"[Esp32CamClient] Starting preview from {self.snapshot_url} (press 'q' to quit)")
        for frame in self.iter_frames(delay=delay):
            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()
