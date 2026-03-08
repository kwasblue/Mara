# schema/commands/_stepper.py
"""Stepper motor command definitions."""

STEPPER_COMMANDS: dict[str, dict] = {
    "CMD_STEPPER_MOVE_REL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Move a stepper a relative number of steps.",
        "payload": {
            "motor_id": {"type": "int", "required": True},
            "steps": {"type": "int", "required": True},
            "speed_steps_s": {
                "type": "float",
                "required": False,
                "default": 1000.0,
            },
        },
    },

    "CMD_STEPPER_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Immediately stop a stepper motor.",
        "payload": {
            "motor_id": {"type": "int", "required": True},
        },
    },

    "CMD_STEPPER_ENABLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Enable or disable a stepper driver (via enable pin).",
        "payload": {
            "motor_id": {"type": "int", "required": True},
            "enable": {
                "type": "bool",
                "required": False,
                "default": True,
            },
        },
    },
}
