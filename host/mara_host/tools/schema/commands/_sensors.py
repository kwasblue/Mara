# schema/commands/_sensors.py
"""Sensor command definitions (ultrasonic, encoder, IMU)."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SENSOR_COMMAND_OBJECTS: dict[str, CommandDef] = {
    # IMU Commands
    "CMD_IMU_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Request a one-shot IMU snapshot and return it directly in the ACK payload.",
    ),
    "CMD_IMU_CALIBRATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Calibrate the IMU by collecting samples to compute bias offsets.",
        payload={
            "samples": FieldDef(type="int", default=100, description="Number of samples to collect."),
            "delay_ms": FieldDef(type="int", default=10, description="Delay between samples in milliseconds."),
        },
    ),
    "CMD_IMU_SET_BIAS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set IMU bias offsets directly.",
        payload={
            "accel_bias": FieldDef(type="array", required=True, description="Accelerometer bias [ax, ay, az]."),
            "gyro_bias": FieldDef(type="array", required=True, description="Gyroscope bias [gx, gy, gz]."),
        },
    ),
    "CMD_IMU_ZERO": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Zero the IMU orientation (reset yaw/heading).",
    ),
    "CMD_I2C_SCAN": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Scan the primary MCU I2C bus and report responding 7-bit addresses.",
    ),
    # Ultrasonic Commands
    "CMD_ULTRASONIC_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach/configure an ultrasonic sensor for the given logical sensor_id.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, default=0),
            "trig_pin": FieldDef(type="int", required=True, description="Trigger pin number."),
            "echo_pin": FieldDef(type="int", required=True, description="Echo pin number."),
            "max_distance_cm": FieldDef(type="float", default=400.0, description="Maximum detection distance in cm."),
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
    # Encoder Commands
    "CMD_ENCODER_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach/configure a quadrature encoder with runtime pins.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, default=0),
            "pin_a": FieldDef(type="int", required=True, description="Phase A / CLK pin."),
            "pin_b": FieldDef(type="int", required=True, description="Phase B / DT pin."),
            "ppr": FieldDef(type="int", default=11, description="Pulses per revolution."),
            "gear_ratio": FieldDef(type="float", default=1.0, description="Gear ratio for geared motors."),
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
    "CMD_ENCODER_DETACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Detach an encoder and free its resources.",
        payload={
            "encoder_id": FieldDef(type="int", required=True),
        },
    ),
}

SENSOR_COMMANDS: dict[str, dict] = export_command_dicts(SENSOR_COMMAND_OBJECTS)
