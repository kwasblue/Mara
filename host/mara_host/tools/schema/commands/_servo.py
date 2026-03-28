# schema/commands/_servo.py
"""Servo command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SERVO_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_SERVO_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach a servo ID to a physical pin.",
        payload={
            "servo_id": FieldDef(type="int", required=True),
            "channel": FieldDef(type="int", required=True),
            "min_us": FieldDef(type="int", default=1000),
            "max_us": FieldDef(type="int", default=2000),
        },
    ),
    "CMD_SERVO_DETACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Detach a servo ID.",
        payload={"servo_id": FieldDef(type="int", required=True)},
    ),
    "CMD_SERVO_SET_ANGLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set servo angle in degrees.",
        payload={
            "servo_id": FieldDef(type="int", required=True),
            "angle_deg": FieldDef(type="float", required=True),
            "duration_ms": FieldDef(type="int", default=0, description="Interpolation duration in milliseconds (0 = immediate)."),
        },
    ),
    "CMD_BATCH_APPLY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Apply a staged batch of batchable commands at one control boundary with deterministic MCU family ordering.",
        payload={
            "actions": FieldDef(
                type="array",
                required=True,
                description="Array of action objects shaped like {cmd, args}. Batchable commands: CMD_GPIO_WRITE, CMD_SERVO_SET_ANGLE, CMD_PWM_SET, CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP.",
                items={"type": "object"},
            ),
        },
    ),
}

SERVO_COMMANDS: dict[str, dict] = export_command_dicts(SERVO_COMMAND_OBJECTS)
