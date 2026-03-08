# schema/commands/_motion.py
"""Motion and robot core command definitions."""

MOTION_COMMANDS: dict[str, dict] = {
    "CMD_SET_MODE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set the high-level robot mode. Prefer ARM/ACTIVATE/DISARM/DEACTIVATE.",
        "payload": {
            "mode": {
                "type": "string",
                "required": True,
                "enum": ["IDLE", "ARMED", "ACTIVE", "CALIB"],
            }
        },
    },

    "CMD_SET_VEL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set linear and angular velocity in robot frame.",
        "payload": {
            "vx": {"type": "float", "required": True, "units": "m/s"},
            "omega": {"type": "float", "required": True, "units": "rad/s"},
            "frame": {
                "type": "string",
                "required": False,
                "default": "robot",
                "enum": ["robot", "world"],
            },
        },
    },
}
