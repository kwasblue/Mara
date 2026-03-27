# schema/commands/_servo.py
"""Servo command definitions."""

SERVO_COMMANDS: dict[str, dict] = {
    "CMD_SERVO_ATTACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Attach a servo ID to a physical pin.",
        "payload": {
            "servo_id": {"type": "int", "required": True},
            "channel": {"type": "int", "required": True},
            "min_us": {"type": "int", "required": False, "default": 1000},
            "max_us": {"type": "int", "required": False, "default": 2000},
        },
    },

    "CMD_SERVO_DETACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Detach a servo ID.",
        "payload": {
            "servo_id": {"type": "int", "required": True},
        },
    },

    "CMD_SERVO_SET_ANGLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set servo angle in degrees.",
        "payload": {
            "servo_id": {"type": "int", "required": True},
            "angle_deg": {"type": "float", "required": True},
            "duration_ms": {
                "type": "int",
                "required": False,
                "default": 0,
                "description": "Interpolation duration in milliseconds (0 = immediate).",
            },
        },
    },

    "CMD_BATCH_APPLY": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Apply a staged batch of batchable commands at one control boundary with deterministic MCU family ordering.",
        "payload": {
            "actions": {
                "type": "array",
                "required": True,
                "description": "Array of action objects shaped like {cmd, args}. Batchable commands: CMD_GPIO_WRITE, CMD_SERVO_SET_ANGLE, CMD_PWM_SET, CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP.",
                "items": {"type": "object"},
            },
        },
    },
}
