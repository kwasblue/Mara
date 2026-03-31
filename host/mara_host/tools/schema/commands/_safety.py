# schema/commands/_safety.py
"""Safety and state machine command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SAFETY_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_GET_IDENTITY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get device identity and capabilities (firmware version, build config, features).",
        timeout_s=2.0,
    ),
    "CMD_HEARTBEAT": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Host heartbeat to maintain connection. Resets host timeout watchdog.",
    ),
    "CMD_ARM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Transition from IDLE to ARMED. Motors enabled but not accepting motion.",
        timeout_s=0.5,
    ),
    "CMD_DISARM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Transition from ARMED to IDLE. Motors disabled.",
        timeout_s=0.5,
    ),
    "CMD_ACTIVATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Transition from ARMED to ACTIVE. Motion commands now accepted.",
        timeout_s=0.5,
    ),
    "CMD_DEACTIVATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Transition from ACTIVE to ARMED. Stops motion, still armed.",
        timeout_s=0.5,
    ),
    "CMD_ESTOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Emergency stop, immediately disable motion.",
    ),
    "CMD_CLEAR_ESTOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Clear ESTOP and return to IDLE mode.",
        timeout_s=0.5,
    ),
    "CMD_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Stop all motion (soft stop).",
    ),
    "CMD_GET_STATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Query current MCU state (mode, armed, active, estop).",
        response={
            "mode": FieldDef(type="string", description="Current mode: IDLE, ARMED, ACTIVE, ESTOP"),
            "armed": FieldDef(type="bool", description="True if motors enabled"),
            "active": FieldDef(type="bool", description="True if motion commands accepted"),
            "estop": FieldDef(type="bool", description="True if emergency stop active"),
        },
    ),
    "CMD_GET_SAFETY_TIMEOUTS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Query current safety timeout settings.",
        response={
            "host_timeout_ms": FieldDef(type="int", description="Host heartbeat timeout (0=disabled)"),
            "motion_timeout_ms": FieldDef(type="int", description="Motion command timeout (0=disabled)"),
            "enabled": FieldDef(type="bool", description="True if any timeout is active"),
        },
    ),
    "CMD_SET_SAFETY_TIMEOUTS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set safety timeout values. Use 0 to disable a timeout.",
        payload={
            "host_timeout_ms": FieldDef(type="int", description="Host heartbeat timeout in ms (0=disabled)"),
            "motion_timeout_ms": FieldDef(type="int", description="Motion command timeout in ms (0=disabled)"),
        },
        response={
            "host_timeout_ms": FieldDef(type="int", description="Actual host timeout set"),
            "motion_timeout_ms": FieldDef(type="int", description="Actual motion timeout set"),
            "enabled": FieldDef(type="bool", description="True if any timeout is active"),
        },
    ),
}

SAFETY_COMMANDS: dict[str, dict] = export_command_dicts(SAFETY_COMMAND_OBJECTS)
