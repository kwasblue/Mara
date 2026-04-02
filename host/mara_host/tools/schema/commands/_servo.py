# schema/commands/_servo.py
"""Servo command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SERVO_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_SERVO_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach a servo to a GPIO pin.",
        payload={
            "servo_id": FieldDef(type="int", required=True, description="Servo ID (0-7)"),
            "channel": FieldDef(type="int", required=True, description="GPIO pin number"),
            "min_us": FieldDef(type="int", default=500, description="Min pulse width in microseconds"),
            "max_us": FieldDef(type="int", default=2500, description="Max pulse width in microseconds"),
        },
        response_format="Servo {servo_id} attached to pin {pin}",
        param_overrides={"channel": {"tool_name": "pin"}},
    ),
    "CMD_SERVO_DETACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Detach a servo from its pin.",
        payload={"servo_id": FieldDef(type="int", required=True, description="Servo ID (0-7)")},
        response_format="Servo {servo_id} detached",
    ),
    "CMD_SERVO_SET_ANGLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Move a servo to the specified angle.",
        payload={
            "servo_id": FieldDef(type="int", required=True, description="Servo ID (0-7)"),
            "angle_deg": FieldDef(type="float", required=True, description="Angle in degrees (0-180)"),
            "duration_ms": FieldDef(type="int", default=300, description="Movement duration in ms (0=instant)"),
        },
        tool_name="servo_set",
        response_format="Servo {servo_id} -> {angle}deg",
        param_overrides={"angle_deg": {"tool_name": "angle"}},
    ),
    "CMD_SERVO_SET_PULSE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set servo pulse width directly in microseconds.",
        payload={
            "servo_id": FieldDef(type="int", required=True, description="Servo ID (0-7)"),
            "pulse_us": FieldDef(type="int", required=True, description="Pulse width in microseconds"),
        },
        response_format="Servo {servo_id} pulse={pulse_us}us",
    ),
    "CMD_BATCH_APPLY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Apply a generic staged batch/composite envelope using actions=[{cmd,args}, ...]. Batchable commands: CMD_GPIO_WRITE, CMD_SERVO_SET_ANGLE, CMD_PWM_SET, CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP. MCU apply order is fixed by command family on one control tick.",
        payload={
            "actions": FieldDef(
                type="array",
                required=True,
                description="Array of batch action objects shaped like {cmd, args}.",
                items={"type": "object"},
            ),
        },
        category="batch",
        requires_arm=False,
        response_format="batch_apply OK",
    ),
}

SERVO_COMMANDS: dict[str, dict] = export_command_dicts(SERVO_COMMAND_OBJECTS)
