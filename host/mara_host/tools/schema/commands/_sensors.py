# schema/commands/_sensors.py
"""Sensor command definitions (ultrasonic, encoder, IMU)."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SENSOR_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_IMU_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Request a one-shot IMU snapshot and return it directly in the ACK payload.",
    ),
    "CMD_I2C_SCAN": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Scan the primary MCU I2C bus and report responding 7-bit addresses.",
    ),
    "CMD_ULTRASONIC_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach/configure an ultrasonic sensor for the given logical sensor_id.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, default=0),
        },
    ),
    "CMD_ULTRASONIC_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Trigger a single ultrasonic distance measurement.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, default=0),
        },
    ),
    "CMD_ULTRASONIC_DETACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Detach an ultrasonic sensor and clear its cached state.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, default=0),
        },
    ),
    "CMD_ENCODER_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach/configure a quadrature encoder with runtime pins.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, default=0),
            "pin_a": FieldDef(type="int", required=True, default=32),
            "pin_b": FieldDef(type="int", required=True, default=33),
        },
    ),
    "CMD_ENCODER_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Request current tick count for a given encoder.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, default=0),
        },
    ),
    "CMD_ENCODER_RESET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset the tick count for a given encoder back to zero.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, default=0),
        },
    ),
}

SENSOR_COMMANDS: dict[str, dict] = export_command_dicts(SENSOR_COMMAND_OBJECTS)
