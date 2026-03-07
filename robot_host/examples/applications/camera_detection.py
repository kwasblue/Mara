# robot_host/main_with_camera.py (full example)

import numpy as np

from robot_host.camera import CameraModule
from robot_host.vision import Detection, DetectionModule

# --- dummy model + decoder from above ---

class DummyModel:
    def __call__(self, x):
        boxes = np.array([[0.2, 0.2, 0.8, 0.8]], dtype=np.float32)
        scores = np.array([0.9], dtype=np.float32)
        labels = np.array([0], dtype=np.int32)
        return {"boxes": boxes, "scores": scores, "labels": labels}


def simple_decode_fn(
    raw: dict,
    display_shape: tuple[int, int],
    ml_size: tuple[int, int],
) -> list[Detection]:
    H, W = display_shape
    boxes = raw["boxes"]
    scores = raw["scores"]
    labels = raw["labels"]

    detections: list[Detection] = []
    for box, score, label in zip(boxes, scores, labels):
        x1_n, y1_n, x2_n, y2_n = box
        x1 = int(x1_n * W)
        y1 = int(y1_n * H)
        x2 = int(x2_n * W)
        y2 = int(y2_n * H)
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


def main():
    cam_ip = "http://10.0.0.67"  # replace with your ESP32-CAM URL

    ml_size = (224, 224)

    # Instantiate your detection module
    model = DummyModel()
    detector = DetectionModule(
        model=model,
        decode_fn=simple_decode_fn,
        ml_size=ml_size,
        class_names=["dummy_object"],
        score_thresh=0.5,
        use_torch=False,         # set True and adjust if you use a torch model
        show_window=True,
        window_name="cam:detections",
        publish_fn=None,         # or hook into EventBus here
    )

    cam = CameraModule(
        base_url=cam_ip,
        name="front_cam",
        display_size=(320, 240),
        ml_size=ml_size,
        blur_ksize=3,
        fps=5.0,
        show_preview=False,            # DetectionModule handles its own window
        frame_callback=detector.handle_frame,
    )

    # Foreground mode so OpenCV windows behave correctly on macOS
    cam.run_foreground()


if __name__ == "__main__":
    main()
