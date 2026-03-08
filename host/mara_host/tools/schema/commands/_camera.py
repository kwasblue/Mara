# schema/commands/_camera.py
"""Camera command definitions (ESP32-CAM over HTTP)."""

CAMERA_COMMANDS: dict[str, dict] = {
    "CMD_CAM_GET_STATUS": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Get camera device status (IP, RSSI, heap, uptime).",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
                "description": "Camera ID for multi-camera setups.",
            },
        },
    },

    "CMD_CAM_GET_CONFIG": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Get current camera configuration.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
        },
    },

    "CMD_CAM_SET_RESOLUTION": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set camera resolution. 5=QVGA(320x240), 8=VGA(640x480), 9=SVGA(800x600), 10=XGA(1024x768), 13=UXGA(1600x1200).",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "size": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 13,
                "description": "Frame size enum (0=QQVGA to 13=UXGA).",
            },
        },
    },

    "CMD_CAM_SET_QUALITY": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set JPEG compression quality. Lower values = better quality, larger files.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "quality": {
                "type": "int",
                "required": True,
                "min": 4,
                "max": 63,
                "description": "JPEG quality (4-63, lower is better).",
            },
        },
    },

    "CMD_CAM_SET_BRIGHTNESS": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set image brightness.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "brightness": {
                "type": "int",
                "required": True,
                "min": -2,
                "max": 2,
                "description": "Brightness level (-2 to 2).",
            },
        },
    },

    "CMD_CAM_SET_CONTRAST": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set image contrast.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "contrast": {
                "type": "int",
                "required": True,
                "min": -2,
                "max": 2,
                "description": "Contrast level (-2 to 2).",
            },
        },
    },

    "CMD_CAM_SET_SATURATION": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set color saturation.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "saturation": {
                "type": "int",
                "required": True,
                "min": -2,
                "max": 2,
                "description": "Saturation level (-2 to 2).",
            },
        },
    },

    "CMD_CAM_SET_SHARPNESS": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set image sharpness.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "sharpness": {
                "type": "int",
                "required": True,
                "min": -2,
                "max": 2,
                "description": "Sharpness level (-2 to 2).",
            },
        },
    },

    "CMD_CAM_SET_FLIP": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Set image flip/mirror options.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "hmirror": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Horizontal mirror.",
            },
            "vflip": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Vertical flip.",
            },
        },
    },

    "CMD_CAM_SET_AWB": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Configure auto white balance.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "enabled": {
                "type": "bool",
                "required": True,
                "description": "Enable auto white balance.",
            },
            "mode": {
                "type": "int",
                "required": False,
                "default": 0,
                "min": 0,
                "max": 4,
                "description": "WB mode: 0=Auto, 1=Sunny, 2=Cloudy, 3=Office, 4=Home.",
            },
        },
    },

    "CMD_CAM_SET_EXPOSURE": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Configure exposure settings.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "auto": {
                "type": "bool",
                "required": True,
                "description": "Enable auto exposure.",
            },
            "value": {
                "type": "int",
                "required": False,
                "default": 300,
                "min": 0,
                "max": 1200,
                "description": "Manual exposure value (when auto=false).",
            },
        },
    },

    "CMD_CAM_SET_GAIN": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Configure gain settings.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "auto": {
                "type": "bool",
                "required": True,
                "description": "Enable auto gain control.",
            },
            "value": {
                "type": "int",
                "required": False,
                "default": 0,
                "min": 0,
                "max": 30,
                "description": "Manual gain value (when auto=false).",
            },
            "ceiling": {
                "type": "int",
                "required": False,
                "default": 2,
                "min": 0,
                "max": 6,
                "description": "Gain ceiling (0=2x to 6=128x).",
            },
        },
    },

    "CMD_CAM_FLASH": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Control flash LED.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "state": {
                "type": "string",
                "required": True,
                "enum": ["on", "off", "toggle"],
                "description": "Flash state: on, off, or toggle.",
            },
        },
    },

    "CMD_CAM_APPLY_PRESET": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Apply a predefined camera configuration preset.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "preset": {
                "type": "string",
                "required": True,
                "enum": ["default", "streaming", "high_quality", "fast", "night", "ml_inference"],
                "description": "Preset name.",
            },
        },
    },

    "CMD_CAM_START_CAPTURE": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Start continuous frame capture (polling or streaming mode).",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "mode": {
                "type": "string",
                "required": False,
                "default": "polling",
                "enum": ["polling", "streaming"],
                "description": "Capture mode.",
            },
            "fps": {
                "type": "float",
                "required": False,
                "default": 10.0,
                "description": "Target frame rate (polling mode).",
            },
        },
    },

    "CMD_CAM_STOP_CAPTURE": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Stop continuous frame capture.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
        },
    },

    "CMD_CAM_CAPTURE_FRAME": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Capture a single frame (one-shot).",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "publish": {
                "type": "bool",
                "required": False,
                "default": True,
                "description": "Publish frame to event bus.",
            },
        },
    },

    "CMD_CAM_START_RECORDING": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Start recording frames to disk.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "output_dir": {
                "type": "string",
                "required": False,
                "default": "recordings",
                "description": "Output directory for recordings.",
            },
            "format": {
                "type": "string",
                "required": False,
                "default": "video",
                "enum": ["video", "frames"],
                "description": "Recording format.",
            },
        },
    },

    "CMD_CAM_STOP_RECORDING": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Stop recording.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
        },
    },

    "CMD_CAM_SET_MOTION_DETECTION": {
        "kind": "cmd",
        "direction": "host->camera",
        "description": "Configure motion detection.",
        "payload": {
            "camera_id": {
                "type": "int",
                "required": False,
                "default": 0,
            },
            "enabled": {
                "type": "bool",
                "required": True,
                "description": "Enable motion detection.",
            },
            "sensitivity": {
                "type": "int",
                "required": False,
                "default": 30,
                "min": 1,
                "max": 100,
                "description": "Motion sensitivity (1-100).",
            },
        },
    },
}
