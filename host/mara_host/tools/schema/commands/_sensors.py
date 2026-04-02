# schema/commands/_sensors.py
"""Sensor command definitions (ultrasonic, encoder, IMU)."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


SENSOR_COMMAND_OBJECTS: dict[str, CommandDef] = {
    # IMU Commands
    "CMD_IMU_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Read IMU sensor data (accelerometer and gyroscope).",
        requires_arm=False,
    ),
    "CMD_IMU_CALIBRATE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Auto-calibrate IMU bias by collecting samples.",
        payload={
            "samples": FieldDef(type="int", default=100, description="Number of samples to collect"),
            "delay_ms": FieldDef(type="int", default=10, description="Delay between samples in ms"),
        },
        requires_arm=False,
        response_format="IMU calibration complete",
    ),
    "CMD_IMU_SET_BIAS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set IMU bias offsets manually.",
        payload={
            "accel_bias": FieldDef(type="array", required=True, description="Accelerometer bias [ax, ay, az]"),
            "gyro_bias": FieldDef(type="array", required=True, description="Gyroscope bias [gx, gy, gz]"),
        },
        requires_arm=False,
        response_format="IMU bias set",
    ),
    "CMD_IMU_ZERO": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset IMU orientation (zero yaw/heading).",
        requires_arm=False,
        response_format="IMU zeroed",
    ),
    "CMD_I2C_SCAN": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Scan the MCU primary I2C bus and report responding addresses.",
        category="imu",  # Group with IMU tools
        requires_arm=False,
        tool_name="i2c_scan",
    ),
    # Ultrasonic Commands
    "CMD_ULTRASONIC_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach an ultrasonic distance sensor to GPIO pins.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, description="Sensor ID (0-3)"),
            "trig_pin": FieldDef(type="int", required=True, description="Trigger GPIO pin"),
            "echo_pin": FieldDef(type="int", required=True, description="Echo GPIO pin"),
            "max_distance_cm": FieldDef(type="float", default=400.0, description="Maximum measurable distance in cm"),
        },
        requires_arm=False,
        response_format="Ultrasonic {sensor_id} attached (trig={trig_pin}, echo={echo_pin})",
    ),
    "CMD_ULTRASONIC_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Read distance from ultrasonic sensor in centimeters.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, description="Sensor ID (0-3)"),
        },
        requires_arm=False,
    ),
    "CMD_ULTRASONIC_DETACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Detach an ultrasonic sensor.",
        payload={
            "sensor_id": FieldDef(type="int", required=True, description="Sensor ID (0-3)"),
        },
        requires_arm=False,
        response_format="Ultrasonic {sensor_id} detached",
    ),
    # Encoder Commands
    "CMD_ENCODER_ATTACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Attach a quadrature encoder to GPIO pins.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, description="Encoder ID"),
            "pin_a": FieldDef(type="int", required=True, description="Phase A / CLK pin"),
            "pin_b": FieldDef(type="int", required=True, description="Phase B / DT pin"),
            "ppr": FieldDef(type="int", default=11, description="Pulses per revolution"),
            "gear_ratio": FieldDef(type="float", default=1.0, description="Gear ratio for geared motors"),
        },
        requires_arm=False,
        response_format="Encoder {encoder_id} attached",
    ),
    "CMD_ENCODER_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Read encoder value.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, description="Encoder ID"),
        },
        requires_arm=False,
    ),
    "CMD_ENCODER_RESET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset encoder count to zero.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, description="Encoder ID"),
        },
        requires_arm=False,
        response_format="Encoder {encoder_id} reset",
    ),
    "CMD_ENCODER_DETACH": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Detach an encoder.",
        payload={
            "encoder_id": FieldDef(type="int", required=True, description="Encoder ID"),
        },
        requires_arm=False,
        response_format="Encoder {encoder_id} detached",
    ),
}

SENSOR_COMMANDS: dict[str, dict] = export_command_dicts(SENSOR_COMMAND_OBJECTS)
