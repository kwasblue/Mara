# mara_host/main_with_camera.py

from __future__ import annotations

from typing import Optional

from mara_host.camera import CameraModule
from mara_host.vision import DetectionModule, YoloWrapper, decode_yolo_output


def main():
    cam_ip = "http://10.0.0.67"   # replace with your ESP32-CAM URL

    # ML input size — must match what you want to feed YOLO.
    # YOLO can rescale internally, but keeping this square (e.g. 320x320) is typical.
    ml_size = (320, 320)  # (W_ml, H_ml)

    # 1) Create YOLO wrapper
    yolo = YoloWrapper(weights="yolov8n.pt")  # or your custom weights
    class_names = getattr(yolo, "class_names", None)

    # 2) Create DetectionModule that uses YOLO
    detector = DetectionModule(
        model=yolo,
        decode_fn=decode_yolo_output,
        ml_size=ml_size,
        class_names=class_names,
        score_thresh=0.5,
        use_torch=False,            # YOLO wrapper handles torch internally
        device="cpu",               # ignored since use_torch=False
        show_window=True,
        window_name="cam:yolo",
        publish_fn=None,            # plug EventBus here later if you want
    )

    # 3) Create CameraModule and plug in detector.handle_frame
    cam = CameraModule(
        base_url=cam_ip,
        name="front_cam",
        display_size=(320, 240),
        ml_size=ml_size,
        blur_ksize=0,
        fps=5.0,
        show_preview=False,         # DetectionModule owns the overlay window
        frame_callback=detector.handle_frame,
    )

    # Foreground mode so OpenCV window behaves correctly
    cam.run_foreground()


if __name__ == "__main__":
    main()
