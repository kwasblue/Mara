# schema/commands/_telemetry.py
"""Telemetry and logging command definitions."""

TELEMETRY_COMMANDS: dict[str, dict] = {
    "CMD_TELEM_SET_INTERVAL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set telemetry publish interval in milliseconds (0 = disable).",
        "payload": {
            "interval_ms": {
                "type": "int",
                "required": True,
                "default": 100,
            },
        },
    },

    "CMD_SET_LOG_LEVEL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set MCU logging verbosity level.",
        "payload": {
            "level": {
                "type": "string",
                "required": True,
                "enum": ["debug", "info", "warn", "error", "off"],
                "default": "info",
            },
        },
    },
}
