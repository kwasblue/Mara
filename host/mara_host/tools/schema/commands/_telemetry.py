# schema/commands/_telemetry.py
"""Telemetry and logging command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


TELEMETRY_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_TELEM_SET_INTERVAL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set telemetry publish interval in milliseconds (0 = disable).",
        payload={
            "interval_ms": FieldDef(type="int", required=True, default=100),
        },
    ),
    "CMD_SET_LOG_LEVEL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set MCU logging verbosity level.",
        payload={
            "level": FieldDef(type="string", required=True, default="info", enum=("debug", "info", "warn", "error", "off")),
        },
    ),
}

TELEMETRY_COMMANDS: dict[str, dict] = export_command_dicts(TELEMETRY_COMMAND_OBJECTS)
