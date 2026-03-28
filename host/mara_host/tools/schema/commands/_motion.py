# schema/commands/_motion.py
"""Motion and robot core command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


MOTION_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_SET_MODE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set the high-level robot mode. Prefer ARM/ACTIVATE/DISARM/DEACTIVATE.",
        payload={
            "mode": FieldDef(type="string", required=True, enum=("IDLE", "ARMED", "ACTIVE", "CALIB")),
        },
    ),
    "CMD_SET_VEL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set linear and angular velocity in robot frame.",
        payload={
            "vx": FieldDef(type="float", required=True, units="m/s"),
            "omega": FieldDef(type="float", required=True, units="rad/s"),
            "frame": FieldDef(type="string", default="robot", enum=("robot", "world")),
        },
    ),
}

MOTION_COMMANDS: dict[str, dict] = export_command_dicts(MOTION_COMMAND_OBJECTS)
