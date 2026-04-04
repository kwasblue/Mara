# schema/commands/_safety.py
"""Safety and state machine command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SAFETY_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_GET_IDENTITY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get firmware version, board type, and feature flags.",
        timeout_s=2.0,
        category="system",
        requires_arm=False,
        tool_name="get_identity",
    ),
    "CMD_HEARTBEAT": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Host heartbeat to maintain connection. Resets host timeout watchdog.",
        category="system",
        requires_arm=False,
        skip_tool=True,  # Internal keep-alive, not exposed as tool
    ),
    "CMD_ARM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Arm the robot for operation. Required before moving actuators.",
        timeout_s=0.5,
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_DISARM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Disarm the robot. Stops all motion.",
        timeout_s=0.5,
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_ACTIVATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Activate the robot (ARMED -> ACTIVE). Motion commands are only accepted in ACTIVE state.",
        timeout_s=0.5,
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_DEACTIVATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Deactivate the robot (ACTIVE -> ARMED). Stops accepting motion commands.",
        timeout_s=0.5,
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_ESTOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Emergency stop - immediately halt all motion and enter ESTOP state. Requires clear_estop before resuming.",
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_CLEAR_ESTOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Clear emergency stop condition (ESTOP -> IDLE). Required after estop before normal operation.",
        timeout_s=0.5,
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Soft stop - zero velocities without changing robot state.",
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_GET_STATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Query current robot state from MCU. Returns mode (IDLE/ARMED/ACTIVE/ESTOP), armed status, active status, and estop status.",
        response={
            "mode": FieldDef(type="string", description="Current mode: IDLE, ARMED, ACTIVE, ESTOP"),
            "armed": FieldDef(type="bool", description="True if motors enabled"),
            "active": FieldDef(type="bool", description="True if motion commands accepted"),
            "estop": FieldDef(type="bool", description="True if emergency stop active"),
        },
        category="state",
        requires_arm=False,
        skip_tool=True,  # Tool defined in tool_schema.py to use state_service
    ),
    "CMD_GET_SAFETY_TIMEOUTS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get safety timeout values.",
        response={
            "host_timeout_ms": FieldDef(type="int", description="Host heartbeat timeout (0=disabled)"),
            "motion_timeout_ms": FieldDef(type="int", description="Motion command timeout (0=disabled)"),
            "enabled": FieldDef(type="bool", description="True if any timeout is active"),
        },
        category="safety",
        requires_arm=False,
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
        category="safety",
        requires_arm=False,
    ),
    "CMD_SET_SIGNING_KEY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set the signing key for state transition authentication. First key allowed unconditionally. Key rotation requires current key signature.",
        payload={
            "key": FieldDef(type="string", description="Hex-encoded 256-bit key (64 characters)"),
            "signature": FieldDef(type="string", required=False, description="Signature of new key using current key (required for rotation)"),
        },
        response={
            "key_set": FieldDef(type="bool", description="True if key was set successfully"),
        },
        category="security",
        requires_arm=False,
        skip_tool=True,
    ),
    "CMD_RELEASE_SESSION": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Release session ownership to allow another host to take control.",
        payload={
            "client_id": FieldDef(type="int", required=False, description="Client ID releasing session (optional)"),
        },
        response={
            "released": FieldDef(type="bool", description="True if session was released"),
        },
        category="security",
        requires_arm=False,
        skip_tool=True,
    ),
}

SAFETY_COMMANDS: dict[str, dict] = export_command_dicts(SAFETY_COMMAND_OBJECTS)
