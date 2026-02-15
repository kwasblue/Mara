# robot_host/modules/yolo_decode.py

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from robot_host.module.object_detection import Detection


def decode_yolo_output(
    raw: dict,
    display_shape: Tuple[int, int],
    ml_size: Tuple[int, int],
) -> List[Detection]:
    """
    Convert YOLO output dict -> List[Detection] in *display* pixel coordinates.

    raw:
        {
          "boxes": (N, 4) [x1, y1, x2, y2] in ML frame pixels,
          "scores": (N,),
          "labels": (N,)
        }
    display_shape:
        (H_disp, W_disp) for display_frame
    ml_size:
        (W_ml, H_ml) for ML input
    """
    H_disp, W_disp = display_shape
    W_ml, H_ml = ml_size  # note: ml_size passed as (w, h)

    boxes = raw["boxes"]   # (N, 4) in ML-pixel coords
    scores = raw["scores"] # (N,)
    labels = raw["labels"] # (N,)

    boxes = np.asarray(boxes, dtype=np.float32)
    scores = np.asarray(scores, dtype=np.float32)
    labels = np.asarray(labels, dtype=np.int64)

    # Scale ML coords -> display coords
    sx = W_disp / float(W_ml)
    sy = H_disp / float(H_ml)

    detections: List[Detection] = []
    for box, score, label in zip(boxes, scores, labels):
        x1_ml, y1_ml, x2_ml, y2_ml = box

        x1 = int(x1_ml * sx)
        y1 = int(y1_ml * sy)
        x2 = int(x2_ml * sx)
        y2 = int(y2_ml * sy)

        detections.append(
            Detection(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                score=float(score),
                label=int(label),
            )
        )

    return detections
