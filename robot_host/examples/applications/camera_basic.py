# robot_host/main_with_camera.py (example)

import time
import torch  # if you're using torch; otherwise remove
from typing import Optional

import numpy as np

from robot_host.camera import CameraModule
# from robot_host.core.robot_client import RobotClient   # whatever your host uses
# from robot_host.core.event_bus import EventBus         # if you have one


# Example: optional model hook (can be None for now)
class DummyModel:
    def __call__(self, x: torch.Tensor):
        # placeholder for a real model
        return {"dummy_score": torch.rand(1).item()}



def frame_callback(display_frame: np.ndarray, ml_frame: np.ndarray, ts: float):
    h, w = display_frame.shape[:2]
    print(f"[Camera] frame {w}x{h} at ts={ts:.3f}")
    # Example ML hook:
    # x = torch.from_numpy(ml_frame).unsqueeze(0)
    # with torch.no_grad():
    #     preds = model(x)
    # print(preds)


def main():
    cam_ip = "http://10.0.0.67"  # replace with your ESP32-CAM URL

    cam = CameraModule(
        base_url=cam_ip,
        name="front_cam",
        display_size=(320, 240),
        ml_size=(224, 224),
        blur_ksize=3,
        fps=5.0,
        show_preview=True,          # we *want* a window here
        frame_callback=frame_callback,
    )

    # IMPORTANT: foreground mode, not threaded
    cam.run_foreground()
    # This will block, open a window, and exit when you press 'q' or Ctrl+C


if __name__ == "__main__":
    main()