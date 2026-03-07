#!/usr/bin/env python3
"""
Camera Host Module Demo

Demonstrates the integrated camera module with EventBus:
- Command-based control via EventBus
- Frame publishing to topics
- Preset configurations
- Recording

Usage:
    python -m mara_host.runners.run_camera_host [camera_url]
"""

import sys
import time
import cv2

from mara_host.core.event_bus import EventBus
from mara_host.camera import (
    CameraHostModule,
    CameraFrame,
    MLFrame,
    list_presets,
)
from mara_host.config.command_defs import (
    CMD_CAM_GET_STATUS,
    CMD_CAM_APPLY_PRESET,
    CMD_CAM_START_CAPTURE,
    CMD_CAM_STOP_CAPTURE,
    CMD_CAM_SET_RESOLUTION,
    CMD_CAM_FLASH,
)


def main():
    # Get camera URL from args or use default
    camera_url = sys.argv[1] if len(sys.argv) > 1 else "http://10.0.0.66"
    print(f"Camera Host Module Demo")
    print(f"=======================")
    print(f"Camera URL: {camera_url}")
    print(f"Available presets: {list_presets()}")
    print()

    # Create EventBus
    bus = EventBus()

    # Create camera module
    camera = CameraHostModule(
        bus=bus,
        cameras={0: camera_url},
        ml_size=(224, 224),
        stream_port=81,
    )

    # Track frames received
    frame_count = 0
    last_frame = None

    def on_frame(frame: CameraFrame):
        nonlocal frame_count, last_frame
        frame_count += 1
        last_frame = frame
        if frame_count % 30 == 0:
            print(f"[Frame {frame.sequence}] Size: {frame.data.shape}, "
                  f"Latency: {frame.latency_ms:.0f}ms")

    def on_ml_frame(ml_frame: MLFrame):
        if ml_frame.sequence % 30 == 0:
            print(f"[ML Frame {ml_frame.sequence}] Shape: {ml_frame.data.shape}, "
                  f"Range: [{ml_frame.data.min():.3f}, {ml_frame.data.max():.3f}]")

    def on_status(status):
        print(f"[Status] Connected: {status.connected}, IP: {status.ip}, "
              f"RSSI: {status.rssi}dBm, Heap: {status.free_heap//1024}KB")

    def on_config(config):
        print(f"[Config] Resolution: {config.frame_size.name}, Quality: {config.quality}")

    def on_error(error):
        print(f"[Error] {error}")

    # Subscribe to camera events
    bus.subscribe("camera.frame.0", on_frame)
    bus.subscribe("camera.ml_frame.0", on_ml_frame)
    bus.subscribe("camera.status.0", on_status)
    bus.subscribe("camera.config.0", on_config)
    bus.subscribe("camera.error", on_error)

    print("Subscribed to camera events")
    print()

    # Demo: Get status via command
    print(">>> Sending CMD_CAM_GET_STATUS")
    bus.publish("cmd.camera", {"cmd": CMD_CAM_GET_STATUS, "camera_id": 0})
    time.sleep(0.5)

    # Demo: Apply streaming preset
    print("\n>>> Sending CMD_CAM_APPLY_PRESET: streaming")
    bus.publish("cmd.camera", {
        "cmd": CMD_CAM_APPLY_PRESET,
        "camera_id": 0,
        "preset": "streaming",
    })
    time.sleep(0.5)

    # Demo: Start capture in streaming mode (faster than polling)
    print("\n>>> Sending CMD_CAM_START_CAPTURE (streaming mode)")
    bus.publish("cmd.camera", {
        "cmd": CMD_CAM_START_CAPTURE,
        "camera_id": 0,
        "mode": "streaming",  # Use MJPEG stream for better FPS
    })

    # Run for a few seconds with preview
    print("\n>>> Capturing frames via MJPEG stream...")
    print("    Presets: 1=fast, 2=high_quality, 3=night, 4=ml_inference, 5=surveillance, 6=bright")
    print("    Controls: f=flash, d=default, q=quit")
    print()

    cv2.namedWindow("Camera Host Demo", cv2.WINDOW_NORMAL)
    start_time = time.time()

    try:
        while True:
            # Show latest frame
            if last_frame is not None:
                display = last_frame.data.copy()
                # Add overlay
                text = f"Frame: {last_frame.sequence} | FPS: {frame_count / (time.time() - start_time):.1f}"
                cv2.putText(display, text, (10, 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Camera Host Demo", display)

            key = cv2.waitKey(50) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('f'):
                print(">>> Toggling flash")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_FLASH,
                    "camera_id": 0,
                    "state": "toggle",
                })
            elif key == ord('1'):
                print(">>> Applying preset: fast")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "fast",
                })
            elif key == ord('2'):
                print(">>> Applying preset: high_quality")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "high_quality",
                })
            elif key == ord('3'):
                print(">>> Applying preset: night")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "night",
                })
            elif key == ord('4'):
                print(">>> Applying preset: ml_inference")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "ml_inference",
                })
            elif key == ord('5'):
                print(">>> Applying preset: surveillance")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "surveillance",
                })
            elif key == ord('6'):
                print(">>> Applying preset: bright")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "bright",
                })
            elif key == ord('d'):
                print(">>> Applying preset: default")
                bus.publish("cmd.camera", {
                    "cmd": CMD_CAM_APPLY_PRESET,
                    "camera_id": 0,
                    "preset": "default",
                })

    except KeyboardInterrupt:
        pass
    finally:
        print("\n>>> Stopping capture")
        bus.publish("cmd.camera", {"cmd": CMD_CAM_STOP_CAPTURE, "camera_id": 0})
        camera.shutdown()
        cv2.destroyAllWindows()

    print(f"\nTotal frames captured: {frame_count}")
    print(f"Average FPS: {frame_count / (time.time() - start_time):.1f}")


if __name__ == "__main__":
    main()
