# robot_host/modules/detection_module.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple

import cv2
import numpy as np


@dataclass
class Detection:
    """
    Single detection in image (pixel coordinates in *display* frame).
    """
    x1: int
    y1: int
    x2: int
    y2: int
    score: float
    label: int


# ModelOutput -> List[Detection]
DecodeFn = Callable[[Any, Tuple[int, int], Tuple[int, int]], List[Detection]]
# signature: decode_fn(raw_output, display_shape=(H,W), ml_size=(W,H)) -> detections


class DetectionModule:
    """
    Wraps an object detection model and draws results on frames.

    Usage:
      - Create with a `model` and `decode_fn`.
      - Pass `DetectionModule.handle_frame` as the CameraModule.frame_callback.
      - Optionally shows its own window with overlayed boxes.
    """

    def __init__(
        self,
        model: Callable[[Any], Any],
        decode_fn: DecodeFn,
        ml_size: Tuple[int, int],
        class_names: Optional[Sequence[str]] = None,
        score_thresh: float = 0.5,
        use_torch: bool = False,
        device: str = "cpu",
        show_window: bool = True,
        window_name: str = "detections",
        publish_fn: Optional[Callable[[List[Detection], float], None]] = None,
    ) -> None:
        """
        :param model:      Callable that takes an input tensor/array and returns raw detections.
        :param decode_fn:  Function that converts model output -> List[Detection].
        :param ml_size:    (w, h) of ml_frame expected by the model (same as CameraModule.ml_size).
        :param class_names: Optional list of label names, indexed by detection.label.
        :param score_thresh: Minimum score to draw/show detections (enforced by decode_fn if desired).
        :param use_torch:  If True, convert ml_frame (C,H,W) to torch.Tensor before model call.
        :param device:     Torch device string if use_torch=True.
        :param show_window: If True, opens its own OpenCV window with overlays.
        :param window_name: Name of the OpenCV window.
        :param publish_fn: Optional callback(detections, ts) for event bus / logging.
        """
        self.model = model
        self.decode_fn = decode_fn
        self.ml_size = ml_size
        self.class_names = list(class_names) if class_names is not None else None
        self.score_thresh = score_thresh
        self.use_torch = use_torch
        self.device = device
        self.show_window = show_window
        self.window_name = window_name
        self.publish_fn = publish_fn

        if self.show_window:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        if self.use_torch:
            try:
                import torch  # type: ignore[import-not-found]
            except ImportError as e:
                raise RuntimeError("DetectionModule(use_torch=True) but torch not installed") from e
            self._torch = torch
        else:
            self._torch = None

    # This matches CameraModule.FrameCallback: (display_frame, ml_frame, ts) -> None
    def handle_frame(self, display_frame: np.ndarray, ml_frame: np.ndarray, ts: float) -> None:
        """
        Called per frame by CameraModule. Runs the model, decodes detections,
        draws them on a copy of display_frame, shows window, and optionally publishes.
        """
        # Prepare model input
        if self.use_torch:
            # ml_frame is CHW float32 in [0,1], per your CameraModule.get_dual_frame config
            x = self._torch.from_numpy(ml_frame).unsqueeze(0).to(self.device)
            with self._torch.no_grad():
                raw = self.model(x)
        else:
            # Pass numpy array directly; model must handle shape/normalization
            x = ml_frame[None, ...]  # add batch dim
            raw = self.model(x)

        # Decode to list[Detection] *in display pixel coordinates*
        H, W = display_frame.shape[:2]
        detections = self.decode_fn(raw, (H, W), self.ml_size)

        # Optional publish for other modules
        if self.publish_fn is not None:
            try:
                self.publish_fn(detections, ts)
            except Exception as e:
                print(f"[DetectionModule] publish_fn error: {e}")

        # Draw on a copy so we don't mutate the original (in case caller reuses it)
        overlay = display_frame.copy()

        for det in detections:
            if det.score < self.score_thresh:
                continue

            color = (0, 255, 0)  # green box
            cv2.rectangle(overlay, (det.x1, det.y1), (det.x2, det.y2), color, 2)

            label_str = str(det.label)
            if self.class_names is not None and 0 <= det.label < len(self.class_names):
                label_str = self.class_names[det.label]

            text = f"{label_str} {det.score:.2f}"
            cv2.putText(
                overlay,
                text,
                (det.x1, max(det.y1 - 5, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

        if self.show_window:
            cv2.imshow(self.window_name, overlay)
            # Small wait so the window updates
            cv2.waitKey(1)
