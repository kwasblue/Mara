# schema/commands/_rates.py
"""Loop rate command definitions."""

RATE_COMMANDS: dict[str, dict] = {
    "CMD_GET_RATES": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get current loop rates (ctrl, safety, telem) in Hz.",
        "payload": {},
    },

    "CMD_CTRL_SET_RATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set control loop rate in Hz. Only allowed when IDLE.",
        "payload": {
            "hz": {
                "type": "int",
                "required": True,
                "min": 5,
                "max": 200,
                "description": "Control loop frequency in Hz.",
            },
        },
    },

    "CMD_SAFETY_SET_RATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set safety loop rate in Hz. Only allowed when IDLE.",
        "payload": {
            "hz": {
                "type": "int",
                "required": True,
                "min": 20,
                "max": 500,
                "description": "Safety loop frequency in Hz.",
            },
        },
    },

    "CMD_TELEM_SET_RATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set telemetry loop rate in Hz. Only allowed when IDLE.",
        "payload": {
            "hz": {
                "type": "int",
                "required": True,
                "min": 1,
                "max": 50,
                "description": "Telemetry loop frequency in Hz.",
            },
        },
    },
}
