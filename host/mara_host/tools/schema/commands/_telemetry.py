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
        description="Set MCU global logging verbosity level.",
        payload={
            "level": FieldDef(type="string", required=True, default="info", enum=("debug", "info", "warn", "error", "off")),
        },
    ),
    "CMD_SET_SUBSYSTEM_LOG_LEVEL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set logging verbosity for a specific MCU subsystem (e.g., servo, stepper, motor).",
        payload={
            "subsystem": FieldDef(type="string", required=True, description="Subsystem name (e.g., 'servo', 'stepper', 'motor', 'gpio', 'system')"),
            "level": FieldDef(type="string", required=True, default="info", enum=("debug", "info", "warn", "error", "off"), description="Log level. 'off' reverts to global level."),
        },
    ),
    "CMD_GET_LOG_LEVELS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get current MCU log levels (global and per-subsystem).",
        payload={},
    ),
    "CMD_CLEAR_SUBSYSTEM_LOG_LEVELS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Clear all per-subsystem log levels, reverting to global level.",
        payload={},
    ),
}

TELEMETRY_COMMANDS: dict[str, dict] = export_command_dicts(TELEMETRY_COMMAND_OBJECTS)
