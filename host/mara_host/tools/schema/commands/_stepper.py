# schema/commands/_stepper.py
"""Stepper motor command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


STEPPER_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_STEPPER_MOVE_REL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move a stepper a relative number of steps.",
        payload={
            "motor_id": FieldDef(type="int", required=True),
            "steps": FieldDef(type="int", required=True),
            "speed_steps_s": FieldDef(type="float", default=1000.0),
        },
    ),
    "CMD_STEPPER_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Immediately stop a stepper motor.",
        payload={"motor_id": FieldDef(type="int", required=True)},
    ),
    "CMD_STEPPER_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable a stepper driver (via enable pin).",
        payload={
            "motor_id": FieldDef(type="int", required=True),
            "enable": FieldDef(type="bool", default=True),
        },
    ),
}

STEPPER_COMMANDS: dict[str, dict] = export_command_dicts(STEPPER_COMMAND_OBJECTS)
