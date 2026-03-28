# schema/commands/_rates.py
"""Loop rate command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


RATE_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_GET_RATES": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get current loop rates (ctrl, safety, telem) in Hz.",
    ),
    "CMD_CTRL_SET_RATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set control loop rate in Hz. Only allowed when IDLE.",
        payload={
            "hz": FieldDef(type="int", required=True, minimum=5, maximum=200, description="Control loop frequency in Hz."),
        },
    ),
    "CMD_SAFETY_SET_RATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set safety loop rate in Hz. Only allowed when IDLE.",
        payload={
            "hz": FieldDef(type="int", required=True, minimum=20, maximum=500, description="Safety loop frequency in Hz."),
        },
    ),
    "CMD_TELEM_SET_RATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set telemetry loop rate in Hz. Only allowed when IDLE.",
        payload={
            "hz": FieldDef(type="int", required=True, minimum=1, maximum=50, description="Telemetry loop frequency in Hz."),
        },
    ),
}

RATE_COMMANDS: dict[str, dict] = export_command_dicts(RATE_COMMAND_OBJECTS)
