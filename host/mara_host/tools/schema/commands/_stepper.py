# schema/commands/_stepper.py
"""Stepper motor command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


STEPPER_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_STEPPER_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable a stepper driver (via enable pin).",
        payload={
            "stepper_id": FieldDef(type="int", required=True),
            "enable": FieldDef(type="bool", default=True),
        },
    ),
    "CMD_STEPPER_MOVE_REL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move a stepper a relative number of steps.",
        payload={
            "stepper_id": FieldDef(type="int", required=True),
            "steps": FieldDef(type="int", required=True),
            "speed_rps": FieldDef(type="float", default=1.0, description="Speed in revolutions per second."),
        },
    ),
    "CMD_STEPPER_MOVE_DEG": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move a stepper a relative number of degrees.",
        payload={
            "stepper_id": FieldDef(type="int", required=True),
            "degrees": FieldDef(type="float", required=True),
            "speed_rps": FieldDef(type="float", default=1.0, description="Speed in revolutions per second."),
        },
    ),
    "CMD_STEPPER_MOVE_REV": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move a stepper a relative number of revolutions.",
        payload={
            "stepper_id": FieldDef(type="int", required=True),
            "revolutions": FieldDef(type="float", required=True),
            "speed_rps": FieldDef(type="float", default=1.0, description="Speed in revolutions per second."),
        },
    ),
    "CMD_STEPPER_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Immediately stop a stepper motor.",
        payload={"stepper_id": FieldDef(type="int", required=True)},
    ),
    "CMD_STEPPER_GET_POSITION": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get the current position of a stepper motor in steps.",
        payload={"stepper_id": FieldDef(type="int", required=True)},
    ),
    "CMD_STEPPER_RESET_POSITION": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset the stepper position counter to zero.",
        payload={"stepper_id": FieldDef(type="int", required=True)},
    ),
}

STEPPER_COMMANDS: dict[str, dict] = export_command_dicts(STEPPER_COMMAND_OBJECTS)
