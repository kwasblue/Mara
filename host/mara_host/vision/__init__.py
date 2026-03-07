# mara_host/vision/__init__.py
"""
Vision and ML utilities for mara_host.

REQUIRES: Install with vision extras: pip install mara-host[vision]

Includes object detection, YOLO wrapper, and image preprocessing.
"""

try:
    import numpy as np
    import cv2
    _HAS_VISION_DEPS = True
except ImportError as e:
    _HAS_VISION_DEPS = False
    _IMPORT_ERROR = e


def _check_vision_deps():
    """Raise helpful error if vision dependencies not installed."""
    if not _HAS_VISION_DEPS:
        raise ImportError(
            "Vision module requires vision dependencies. "
            "Install with: pip install mara-host[vision]\n"
            f"Missing: {_IMPORT_ERROR}"
        )


def __getattr__(name: str):
    """Lazy import with dependency check."""
    _check_vision_deps()

    if name in ("Detection", "DetectionModule", "DecodeFn"):
        from . import object_detection
        return getattr(object_detection, name)
    elif name == "decode_yolo_output":
        from .yolo_decode import decode_yolo_output
        return decode_yolo_output
    elif name == "YoloWrapper":
        from .yolo_detect import YoloWrapper
        return YoloWrapper
    elif name in ("preprocess_for_ml", "IMAGENET_MEAN", "IMAGENET_STD"):
        from . import ml_preprocess
        return getattr(ml_preprocess, name)

    raise AttributeError(f"module 'mara_host.vision' has no attribute '{name}'")


__all__ = [
    # Detection
    "Detection",
    "DetectionModule",
    "DecodeFn",
    # YOLO
    "YoloWrapper",
    "decode_yolo_output",
    # Preprocessing
    "preprocess_for_ml",
    "IMAGENET_MEAN",
    "IMAGENET_STD",
]
