# schema/commands/_dc_motor.py
"""DC motor command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


DC_MOTOR_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_DC_SET_SPEED": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set DC motor speed and direction for a given motor ID.",
        payload={
            "motor_id": FieldDef(type="int", required=True, description="Logical DC motor ID (0..3)."),
            "speed": FieldDef(
                type="float",
                required=True,
                description="Normalized speed in [-1.0, 1.0]; sign = direction.",
                minimum=-1.0,
                maximum=1.0,
            ),
        },
    ),
    "CMD_DC_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Stop a DC motor (set speed to zero).",
        payload={
            "motor_id": FieldDef(type="int", required=True, description="Logical DC motor ID (0..3)."),
        },
    ),
    "CMD_DC_VEL_PID_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable closed-loop velocity PID control for a DC motor.",
        payload={
            "motor_id": FieldDef(type="int", required=True, description="Logical DC motor ID (0..3)."),
            "enable": FieldDef(type="bool", required=True, description="True to enable velocity PID, False to disable."),
        },
    ),
    "CMD_DC_SET_VEL_TARGET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set desired angular velocity target for a DC motor's PID controller.",
        payload={
            "motor_id": FieldDef(type="int", required=True, description="Logical DC motor ID (0..3)."),
            "omega": FieldDef(type="float", required=True, description="Target angular velocity in rad/s (sign indicates direction)."),
        },
    ),
    "CMD_DC_SET_VEL_GAINS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Configure PID gains for DC motor velocity control.",
        payload={
            "motor_id": FieldDef(type="int", required=True, description="Logical DC motor ID (0..3)."),
            "kp": FieldDef(type="float", required=True, description="Proportional gain for velocity PID."),
            "ki": FieldDef(type="float", required=True, description="Integral gain for velocity PID."),
            "kd": FieldDef(type="float", required=True, description="Derivative gain for velocity PID."),
        },
    ),
}

DC_MOTOR_COMMANDS: dict[str, dict] = export_command_dicts(DC_MOTOR_COMMAND_OBJECTS)
