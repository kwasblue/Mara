# robot_host/modules/yolo_wrapper.py

from __future__ import annotations

from typing import Any, Dict

import numpy as np
from ultralytics import YOLO


class YoloWrapper:
    """
    Thin wrapper around ultralytics YOLO so it matches DetectionModule's expectations.

    __call__(x) expects:
        x: np.ndarray of shape (1, C, H, W), float32 in [0,1]
    Returns:
        dict with 'boxes', 'scores', 'labels' (all numpy arrays).
        boxes are xyxy pixel coords in the ML input frame.
    """

    def __init__(self, weights: str = "yolov8n.pt"):
        self.model = YOLO(weights)

        # Try to grab class names if available
        names = getattr(self.model, "names", None)
        if names is None and hasattr(self.model, "model"):
            names = getattr(self.model.model, "names", None)
        self.class_names = names

    def __call__(self, x: np.ndarray) -> Dict[str, np.ndarray]:
        # x: (1, C, H, W) float32 in [0,1]
        chw = x[0]  # (C, H, W)
        C, H, W = chw.shape

        # Convert to HWC uint8 [0,255]
        img = (chw.transpose(1, 2, 0) * 255.0).clip(0, 255).astype("uint8")

        # YOLO expects BGR or RGB depending on version; by default it handles OpenCV-style BGR fine.
        # Run inference
        results = self.model(img, verbose=False)[0]

        if results.boxes is None or len(results.boxes) == 0:
            # Return empty arrays with correct shapes
            boxes = np.zeros((0, 4), dtype=np.float32)
            scores = np.zeros((0,), dtype=np.float32)
            labels = np.zeros((0,), dtype=np.int64)
            return {"boxes": boxes, "scores": scores, "labels": labels}

        boxes = results.boxes.xyxy.cpu().numpy().astype("float32")   # (N, 4), pixel coords in ML frame
        scores = results.boxes.conf.cpu().numpy().astype("float32")  # (N,)
        labels = results.boxes.cls.cpu().numpy().astype("int64")     # (N,)

        return {"boxes": boxes, "scores": scores, "labels": labels}
