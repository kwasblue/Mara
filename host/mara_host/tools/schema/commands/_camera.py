# schema/commands/_camera.py
"""Camera command definitions (ESP32-CAM over HTTP)."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


_CAMERA_ID = {"camera_id": FieldDef(type="int", default=0, description="Camera ID for multi-camera setups.")}

CAMERA_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_CAM_GET_STATUS": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Get camera device status (IP, RSSI, heap, uptime).",
        payload=_CAMERA_ID,
    ),
    "CMD_CAM_GET_CONFIG": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Get current camera configuration.",
        payload={"camera_id": FieldDef(type="int", default=0)},
    ),
    "CMD_CAM_SET_RESOLUTION": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set camera resolution. 5=QVGA(320x240), 8=VGA(640x480), 9=SVGA(800x600), 10=XGA(1024x768), 13=UXGA(1600x1200).",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "size": FieldDef(type="int", required=True, minimum=0, maximum=13, description="Frame size enum (0=QQVGA to 13=UXGA)."),
        },
    ),
    "CMD_CAM_SET_QUALITY": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set JPEG compression quality. Lower values = better quality, larger files.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "quality": FieldDef(type="int", required=True, minimum=4, maximum=63, description="JPEG quality (4-63, lower is better)."),
        },
    ),
    "CMD_CAM_SET_BRIGHTNESS": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set image brightness.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "brightness": FieldDef(type="int", required=True, minimum=-2, maximum=2, description="Brightness level (-2 to 2)."),
        },
    ),
    "CMD_CAM_SET_CONTRAST": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set image contrast.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "contrast": FieldDef(type="int", required=True, minimum=-2, maximum=2, description="Contrast level (-2 to 2)."),
        },
    ),
    "CMD_CAM_SET_SATURATION": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set color saturation.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "saturation": FieldDef(type="int", required=True, minimum=-2, maximum=2, description="Saturation level (-2 to 2)."),
        },
    ),
    "CMD_CAM_SET_SHARPNESS": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set image sharpness.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "sharpness": FieldDef(type="int", required=True, minimum=-2, maximum=2, description="Sharpness level (-2 to 2)."),
        },
    ),
    "CMD_CAM_SET_FLIP": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Set image flip/mirror options.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "hmirror": FieldDef(type="bool", default=False, description="Horizontal mirror."),
            "vflip": FieldDef(type="bool", default=False, description="Vertical flip."),
        },
    ),
    "CMD_CAM_SET_AWB": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Configure auto white balance.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "enabled": FieldDef(type="bool", required=True, description="Enable auto white balance."),
            "mode": FieldDef(type="int", default=0, minimum=0, maximum=4, description="WB mode: 0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home."),
        },
    ),
    "CMD_CAM_SET_EXPOSURE": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Configure exposure settings.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "auto": FieldDef(type="bool", required=True, description="Enable auto exposure."),
            "value": FieldDef(type="int", default=300, minimum=0, maximum=1200, description="Manual exposure value (when auto=false)."),
        },
    ),
    "CMD_CAM_SET_GAIN": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Configure gain settings.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "auto": FieldDef(type="bool", required=True, description="Enable auto gain control."),
            "value": FieldDef(type="int", default=0, minimum=0, maximum=30, description="Manual gain value (when auto=false)."),
            "ceiling": FieldDef(type="int", default=2, minimum=0, maximum=6, description="Gain ceiling (0=2x to 6=128x)."),
        },
    ),
    "CMD_CAM_FLASH": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Control flash LED.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "state": FieldDef(type="string", required=True, enum=("on", "off", "toggle"), description="Flash state: on, off, or toggle."),
        },
    ),
    "CMD_CAM_APPLY_PRESET": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Apply a predefined camera configuration preset.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "preset": FieldDef(type="string", required=True, enum=("default", "streaming", "high_quality", "fast", "night", "ml_inference"), description="Preset name."),
        },
    ),
    "CMD_CAM_START_CAPTURE": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Start continuous frame capture (polling or streaming mode).",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "mode": FieldDef(type="string", default="polling", enum=("polling", "streaming"), description="Capture mode."),
            "fps": FieldDef(type="float", default=10.0, description="Target frame rate (polling mode)."),
        },
    ),
    "CMD_CAM_STOP_CAPTURE": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Stop continuous frame capture.",
        payload={"camera_id": FieldDef(type="int", default=0)},
    ),
    "CMD_CAM_CAPTURE_FRAME": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Capture a single frame (one-shot).",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "publish": FieldDef(type="bool", default=True, description="Publish frame to event bus."),
        },
    ),
    "CMD_CAM_START_RECORDING": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Start recording frames to disk.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "output_dir": FieldDef(type="string", default="recordings", description="Output directory for recordings."),
            "format": FieldDef(type="string", default="video", enum=("video", "frames"), description="Recording format."),
        },
    ),
    "CMD_CAM_STOP_RECORDING": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Stop recording.",
        payload={"camera_id": FieldDef(type="int", default=0)},
    ),
    "CMD_CAM_SET_MOTION_DETECTION": CommandDef(
        kind="cmd",
        direction="host->camera",
        description="Configure motion detection.",
        payload={
            "camera_id": FieldDef(type="int", default=0),
            "enabled": FieldDef(type="bool", required=True, description="Enable motion detection."),
            "sensitivity": FieldDef(type="int", default=30, minimum=1, maximum=100, description="Motion sensitivity (1-100)."),
        },
    ),
}

CAMERA_COMMANDS: dict[str, dict] = export_command_dicts(CAMERA_COMMAND_OBJECTS)
