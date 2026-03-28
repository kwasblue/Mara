# schema/commands/_safety.py
"""Safety and state machine command definitions."""

SAFETY_COMMANDS: dict[str, dict] = {
    "CMD_GET_IDENTITY": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get device identity and capabilities (firmware version, build config, features).",
        "payload": {},
        "timeout_s": 2.0,  # Identity query may take longer on boot
    },

    "CMD_HEARTBEAT": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Host heartbeat to maintain connection. Resets host timeout watchdog.",
        "payload": {},
        # Uses default timeout (fast command)
    },

    "CMD_ARM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from IDLE to ARMED. Motors enabled but not accepting motion.",
        "payload": {},
        "timeout_s": 0.5,  # State transitions may take slightly longer
    },

    "CMD_DISARM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ARMED to IDLE. Motors disabled.",
        "payload": {},
        "timeout_s": 0.5,
    },

    "CMD_ACTIVATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ARMED to ACTIVE. Motion commands now accepted.",
        "payload": {},
        "timeout_s": 0.5,
    },

    "CMD_DEACTIVATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ACTIVE to ARMED. Stops motion, still armed.",
        "payload": {},
        "timeout_s": 0.5,
    },

    "CMD_ESTOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Emergency stop, immediately disable motion.",
        "payload": {},
        # Uses default timeout - ESTOP must be fast
    },

    "CMD_CLEAR_ESTOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Clear ESTOP and return to IDLE mode.",
        "payload": {},
        "timeout_s": 0.5,
    },

    "CMD_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Stop all motion (soft stop).",
        "payload": {},
        # Uses default timeout - STOP must be fast
    },

    "CMD_GET_STATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Query current MCU state (mode, armed, active, estop).",
        "payload": {},
        "response": {
            "mode": {"type": "string", "description": "Current mode: IDLE, ARMED, ACTIVE, ESTOP"},
            "armed": {"type": "bool", "description": "True if motors enabled"},
            "active": {"type": "bool", "description": "True if motion commands accepted"},
            "estop": {"type": "bool", "description": "True if emergency stop active"},
        },
    },
}
