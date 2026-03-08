# schema/commands/_dc_motor.py
"""DC motor command definitions."""

DC_MOTOR_COMMANDS: dict[str, dict] = {
    "CMD_DC_SET_SPEED": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set DC motor speed and direction for a given motor ID.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "speed": {
                "type": "float",
                "required": True,
                "description": "Normalized speed in [-1.0, 1.0]; sign = direction.",
                "min": -1.0,
                "max": 1.0,
            },
        },
    },

    "CMD_DC_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Stop a DC motor (set speed to zero).",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
        },
    },

    # Velocity PID
    "CMD_DC_VEL_PID_ENABLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Enable or disable closed-loop velocity PID control for a DC motor.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "enable": {
                "type": "bool",
                "required": True,
                "description": "True to enable velocity PID, False to disable.",
            },
        },
    },

    "CMD_DC_SET_VEL_TARGET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set desired angular velocity target for a DC motor's PID controller.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "omega": {
                "type": "float",
                "required": True,
                "description": "Target angular velocity in rad/s (sign indicates direction).",
            },
        },
    },

    "CMD_DC_SET_VEL_GAINS": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Configure PID gains for DC motor velocity control.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "kp": {
                "type": "float",
                "required": True,
                "description": "Proportional gain for velocity PID.",
            },
            "ki": {
                "type": "float",
                "required": True,
                "description": "Integral gain for velocity PID.",
            },
            "kd": {
                "type": "float",
                "required": True,
                "description": "Derivative gain for velocity PID.",
            },
        },
    },
}
