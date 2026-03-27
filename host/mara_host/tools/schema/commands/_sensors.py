# schema/commands/_sensors.py
"""Sensor command definitions (ultrasonic, encoder, IMU)."""

SENSOR_COMMANDS: dict[str, dict] = {
    # IMU
    "CMD_IMU_READ": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Request a one-shot IMU snapshot and return it directly in the ACK payload.",
        "payload": {},
    },
    "CMD_I2C_SCAN": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Scan the primary MCU I2C bus and report responding 7-bit addresses.",
        "payload": {},
    },

    # Ultrasonic
    "CMD_ULTRASONIC_ATTACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Attach/configure an ultrasonic sensor for the given logical sensor_id.",
        "payload": {
            "sensor_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    "CMD_ULTRASONIC_READ": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Trigger a single ultrasonic distance measurement.",
        "payload": {
            "sensor_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    # Encoders
    "CMD_ENCODER_ATTACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Attach/configure a quadrature encoder with runtime pins.",
        "payload": {
            "encoder_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
            "pin_a": {
                "type": "int",
                "required": True,
                "default": 32,
            },
            "pin_b": {
                "type": "int",
                "required": True,
                "default": 33,
            },
        },
    },

    "CMD_ENCODER_READ": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Request current tick count for a given encoder.",
        "payload": {
            "encoder_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    "CMD_ENCODER_RESET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Reset the tick count for a given encoder back to zero.",
        "payload": {
            "encoder_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },
}
