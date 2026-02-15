# Camera Host Module

Integrates ESP32-CAM into the MARA robot host architecture with EventBus-based control, frame publishing, and ML preprocessing.

## Features

- **EventBus Integration**: Commands via `cmd.camera`, frames published to topics
- **Multi-Camera Support**: Manage multiple cameras with unique IDs
- **Capture Modes**: Polling (single frames) or MJPEG streaming (~15 FPS)
- **ML Preprocessing**: Auto-resize to 224x224, ImageNet normalization, CHW format
- **9 Presets**: Optimized configurations for different scenarios
- **Recording**: Save frames as video or image sequences
- **Runtime Control**: Resolution, quality, brightness, contrast, exposure, gain, flash

## Quick Start

```python
from robot_host.core.event_bus import EventBus
from robot_host.module.camera import CameraHostModule

bus = EventBus()

# Initialize camera module
camera = CameraHostModule(
    bus=bus,
    cameras={0: "http://10.0.0.66"},
    ml_size=(224, 224),
    stream_port=81,
)

# Subscribe to frames
def on_frame(frame):
    print(f"Frame {frame.sequence}: {frame.data.shape}")

def on_ml_frame(ml_frame):
    # Ready for inference: (3, 224, 224), normalized
    print(f"ML Frame: {ml_frame.data.shape}")

bus.subscribe("camera.frame.0", on_frame)
bus.subscribe("camera.ml_frame.0", on_ml_frame)

# Start streaming
bus.publish("cmd.camera", {
    "cmd": "CMD_CAM_START_CAPTURE",
    "camera_id": 0,
    "mode": "streaming",
})
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Application                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  CameraHostModule                       │ │
│  │  ┌──────────┬──────────┬──────────┬──────────────────┐ │ │
│  │  │ Commands │ Presets  │ Capture  │ ML Preprocessing │ │ │
│  │  │ Handler  │ Manager  │ Thread   │ (224x224, CHW)   │ │ │
│  │  └──────────┴──────────┴──────────┴──────────────────┘ │ │
│  └────────────────────────┬───────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────┴───────────────────────────────┐ │
│  │                       EventBus                          │ │
│  │  cmd.camera → │ ← camera.frame.0, camera.ml_frame.0    │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────┴───────────────────────────────┐ │
│  │                  Camera Clients                         │ │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐ │ │
│  │  │ Esp32CamClient  │  │ MjpegStreamClient            │ │ │
│  │  │ (REST API)      │  │ (MJPEG Stream, port 81)      │ │ │
│  │  └─────────────────┘  └──────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                   ┌────────┴────────┐
                   │   ESP32-CAM     │
                   │  (WiFi Camera)  │
                   └─────────────────┘
```

## EventBus Topics

### Commands (Subscribe)

| Topic | Description |
|-------|-------------|
| `cmd.camera` | Camera commands (see Commands section) |

### Events (Publish)

| Topic | Data Type | Description |
|-------|-----------|-------------|
| `camera.frame.<id>` | `CameraFrame` | BGR image frame |
| `camera.ml_frame.<id>` | `MLFrame` | Preprocessed ML-ready frame |
| `camera.status.<id>` | `CameraStatus` | Device status (IP, RSSI, heap) |
| `camera.config.<id>` | `CameraConfig` | Current configuration |
| `camera.error` | `dict` | Error messages |

## Commands

Send commands via EventBus to `cmd.camera` topic:

```python
bus.publish("cmd.camera", {"cmd": "CMD_NAME", "camera_id": 0, ...})
```

### Capture Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `CMD_CAM_START_CAPTURE` | `mode` ("streaming"/"polling"), `fps` | Start continuous capture |
| `CMD_CAM_STOP_CAPTURE` | - | Stop capture |
| `CMD_CAM_CAPTURE_FRAME` | `publish` (bool) | Capture single frame |

### Configuration Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `CMD_CAM_APPLY_PRESET` | `preset` (string) | Apply preset configuration |
| `CMD_CAM_SET_RESOLUTION` | `size` (0-14) | Set frame size |
| `CMD_CAM_SET_QUALITY` | `quality` (0-63) | Set JPEG quality (lower=better) |
| `CMD_CAM_SET_BRIGHTNESS` | `brightness` (-2 to 2) | Set brightness |
| `CMD_CAM_SET_CONTRAST` | `contrast` (-2 to 2) | Set contrast |
| `CMD_CAM_SET_SATURATION` | `saturation` (-2 to 2) | Set saturation |
| `CMD_CAM_SET_SHARPNESS` | `sharpness` (-2 to 2) | Set sharpness |
| `CMD_CAM_SET_FLIP` | `hmirror`, `vflip` (bool) | Set image flip |
| `CMD_CAM_SET_AWB` | `enabled`, `mode` (0-4) | Auto white balance |
| `CMD_CAM_SET_EXPOSURE` | `auto`, `value` (0-1200) | Exposure control |
| `CMD_CAM_SET_GAIN` | `auto`, `value`, `ceiling` | Gain control |

### Status Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `CMD_CAM_GET_STATUS` | - | Get device status |
| `CMD_CAM_GET_CONFIG` | - | Get current config |
| `CMD_CAM_FLASH` | `state` ("on"/"off"/"toggle") | Control flash LED |

### Recording Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `CMD_CAM_START_RECORDING` | `output_dir`, `format` | Start recording |
| `CMD_CAM_STOP_RECORDING` | - | Stop recording |
| `CMD_CAM_SET_MOTION_DETECTION` | `enabled`, `sensitivity` | Motion detection |

## Presets

Pre-configured settings optimized for different use cases:

| Preset | Resolution | Quality | Use Case |
|--------|------------|---------|----------|
| `default` | VGA 640x480 | 10 | Balanced starting point |
| `streaming` | VGA 640x480 | 12 | Smooth video, smaller files |
| `high_quality` | SVGA 800x600 | 8 | Best quality |
| `fast` | VGA 640x480 | 12 | Quick response, good visibility |
| `night` | VGA 640x480 | 10 | Low-light (boosted gain/exposure) |
| `ml_inference` | VGA 640x480 | 10 | Optimized for ML models |
| `surveillance` | SVGA 800x600 | 10 | Security recording |
| `timelapse` | SVGA 800x600 | 8 | High quality stills |
| `bright` | VGA 640x480 | 10 | Outdoor/bright conditions |

```python
# Apply a preset
bus.publish("cmd.camera", {
    "cmd": "CMD_CAM_APPLY_PRESET",
    "camera_id": 0,
    "preset": "night",
})
```

## Data Models

### CameraFrame

```python
@dataclass
class CameraFrame:
    camera_id: int
    data: np.ndarray      # BGR image (H, W, 3)
    timestamp: float
    sequence: int
    size_bytes: int
    latency_ms: float
```

### MLFrame

```python
@dataclass
class MLFrame:
    camera_id: int
    data: np.ndarray      # Preprocessed (3, 224, 224), float32
    timestamp: float
    sequence: int
    original_size: tuple[int, int]
```

ML frames are:
- Resized to 224x224
- Normalized with ImageNet mean/std
- Converted to CHW format (channels first)
- Ready for PyTorch/TensorFlow inference

### CameraStatus

```python
@dataclass
class CameraStatus:
    camera_id: int
    connected: bool
    ip: str
    hostname: str
    rssi: int             # WiFi signal strength (dBm)
    free_heap: int        # Available memory (bytes)
    uptime_seconds: int
    flash_on: bool
    streaming: bool
    recording: bool
```

## Multi-Camera Setup

```python
camera = CameraHostModule(
    bus=bus,
    cameras={
        0: "http://10.0.0.66",  # Front camera
        1: "http://10.0.0.67",  # Rear camera
    },
)

# Subscribe to each camera
bus.subscribe("camera.frame.0", handle_front)
bus.subscribe("camera.frame.1", handle_rear)

# Control cameras independently
bus.publish("cmd.camera", {"cmd": "CMD_CAM_APPLY_PRESET", "camera_id": 0, "preset": "fast"})
bus.publish("cmd.camera", {"cmd": "CMD_CAM_APPLY_PRESET", "camera_id": 1, "preset": "surveillance"})
```

## Resolution Reference

| Size | Name | Dimensions |
|------|------|------------|
| 0 | R96X96 | 96x96 |
| 1 | QQVGA | 160x120 |
| 6 | QVGA | 320x240 |
| 9 | VGA | 640x480 |
| 10 | SVGA | 800x600 |
| 11 | XGA | 1024x768 |
| 12 | HD | 1280x720 |
| 13 | SXGA | 1280x1024 |
| 14 | UXGA | 1600x1200 |

**Note**: For stable streaming, use SVGA (800x600) or lower. Higher resolutions may cause instability on ESP32-CAM.

## Example: Vision-Based Robot Control

```python
import asyncio
from robot_host import Robot
from robot_host.core.event_bus import EventBus
from robot_host.module.camera import CameraHostModule

async def main():
    bus = EventBus()

    # Initialize camera
    camera = CameraHostModule(bus, cameras={0: "http://10.0.0.66"})

    # Track latest ML frame
    latest_ml_frame = None

    def on_ml_frame(frame):
        nonlocal latest_ml_frame
        latest_ml_frame = frame

    bus.subscribe("camera.ml_frame.0", on_ml_frame)

    # Start streaming
    bus.publish("cmd.camera", {
        "cmd": "CMD_CAM_START_CAPTURE",
        "camera_id": 0,
        "mode": "streaming",
    })

    async with Robot("/dev/ttyUSB0") as robot:
        await robot.arm()

        while True:
            if latest_ml_frame is not None:
                # Run inference on latest_ml_frame.data
                # Shape: (3, 224, 224), normalized float32
                action = run_model(latest_ml_frame.data)
                await robot.motion.set_velocity(action.vx, action.omega)

            await asyncio.sleep(0.02)  # 50Hz control loop

asyncio.run(main())
```

## Running the Demo

```bash
python -m robot_host.runners.run_camera_host http://10.0.0.66
```

Controls:
- `1-6`: Apply presets (fast, high_quality, night, ml_inference, surveillance, bright)
- `d`: Default preset
- `f`: Toggle flash
- `q`: Quit

## Dependencies

- OpenCV (`cv2`) - Image processing
- NumPy - Array operations
- requests - HTTP client for REST API
