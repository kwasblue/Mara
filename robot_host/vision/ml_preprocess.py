# ml_preprocess.py
import cv2
import numpy as np

# Generic ImageNet-style stats (good default for many models)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_for_ml(
    frame_bgr: np.ndarray,
    target_size=(224, 224),
    normalize: bool = True,
    to_chw: bool = True,
) -> np.ndarray:
    """
    Convert raw OpenCV BGR frame into an ML-ready array.

    Steps:
      - BGR -> RGB
      - Resize to target_size
      - Scale to [0, 1]
      - Optional mean/std normalize
      - Optional CHW (C, H, W)
    """
    # BGR -> RGB
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # Resize
    frame_rgb = cv2.resize(frame_rgb, target_size, interpolation=cv2.INTER_AREA)

    # [0, 1]
    img = frame_rgb.astype(np.float32) / 255.0

    if normalize:
        img = (img - IMAGENET_MEAN) / IMAGENET_STD

    if to_chw:
        img = np.transpose(img, (2, 0, 1))  # HWC -> CHW

    return img
