# schema/commands/_stepper.py
"""Stepper motor command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


STEPPER_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_STEPPER_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable a stepper driver (energize coils).",
        payload={
            "stepper_id": FieldDef(type="int", required=True, description="Stepper ID"),
            "enable": FieldDef(type="bool", default=True, description="True to enable, False to disable"),
        },
        response_format="Stepper {stepper_id} {'enabled' if enable else 'disabled'}",
    ),
    "CMD_STEPPER_MOVE_REL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move stepper motor by relative steps.",
        payload={
            "stepper_id": FieldDef(type="int", required=True, description="Stepper ID"),
            "steps": FieldDef(type="int", required=True, description="Steps to move (negative=reverse)"),
            "speed_rps": FieldDef(type="float", default=1.0, description="Speed in revolutions per second"),
        },
        method_name="move_rel",
        tool_name="stepper_move",
        response_format="Stepper {stepper_id} moved {steps} steps",
    ),
    "CMD_STEPPER_MOVE_DEG": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move stepper motor by degrees.",
        payload={
            "stepper_id": FieldDef(type="int", required=True, description="Stepper ID"),
            "degrees": FieldDef(type="float", required=True, description="Degrees to move"),
            "speed_rps": FieldDef(type="float", default=1.0, description="Speed in revolutions per second"),
        },
        method_name="move_deg",
        response_format="Stepper {stepper_id} moved {degrees}deg",
    ),
    "CMD_STEPPER_MOVE_REV": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move stepper motor by revolutions.",
        payload={
            "stepper_id": FieldDef(type="int", required=True, description="Stepper ID"),
            "revolutions": FieldDef(type="float", required=True, description="Revolutions to move"),
            "speed_rps": FieldDef(type="float", default=1.0, description="Speed in revolutions per second"),
        },
        method_name="move_rev",
        response_format="Stepper {stepper_id} moved {revolutions} revs",
    ),
    "CMD_STEPPER_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Stop a stepper motor.",
        payload={"stepper_id": FieldDef(type="int", required=True, description="Stepper ID")},
        response_format="Stepper {stepper_id} stopped",
    ),
    "CMD_STEPPER_GET_POSITION": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get the current position of a stepper motor in steps.",
        payload={"stepper_id": FieldDef(type="int", required=True, description="Stepper ID")},
        requires_arm=False,
    ),
    "CMD_STEPPER_RESET_POSITION": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset the stepper position counter to zero.",
        payload={"stepper_id": FieldDef(type="int", required=True, description="Stepper ID")},
        requires_arm=False,
        response_format="Stepper {stepper_id} position reset",
    ),
}

STEPPER_COMMANDS: dict[str, dict] = export_command_dicts(STEPPER_COMMAND_OBJECTS)
