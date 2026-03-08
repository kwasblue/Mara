# schema/commands/_safety.py
"""Safety and state machine command definitions."""

SAFETY_COMMANDS: dict[str, dict] = {
    "CMD_GET_IDENTITY": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get device identity and capabilities (firmware version, build config, features).",
        "payload": {},
    },

    "CMD_HEARTBEAT": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Host heartbeat to maintain connection. Resets host timeout watchdog.",
        "payload": {},
    },

    "CMD_ARM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from IDLE to ARMED. Motors enabled but not accepting motion.",
        "payload": {},
    },

    "CMD_DISARM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ARMED to IDLE. Motors disabled.",
        "payload": {},
    },

    "CMD_ACTIVATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ARMED to ACTIVE. Motion commands now accepted.",
        "payload": {},
    },

    "CMD_DEACTIVATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ACTIVE to ARMED. Stops motion, still armed.",
        "payload": {},
    },

    "CMD_ESTOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Emergency stop, immediately disable motion.",
        "payload": {},
    },

    "CMD_CLEAR_ESTOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Clear ESTOP and return to IDLE mode.",
        "payload": {},
    },

    "CMD_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Stop all motion (soft stop).",
        "payload": {},
    },
}
