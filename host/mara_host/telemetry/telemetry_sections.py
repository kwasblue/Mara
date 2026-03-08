# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from TELEMETRY_SECTIONS in schema.py
"""
Binary telemetry section IDs.

These IDs must match the MCU's registerBinProvider() calls.
All section parsers in binary_parser.py use these constants.
"""

# Sensor telemetry sections
TELEM_IMU            = 0x01  # IMU sensor data (accel, gyro, temp)
TELEM_ULTRASONIC     = 0x02  # Ultrasonic distance sensor
TELEM_LIDAR          = 0x03  # LiDAR distance sensor
TELEM_ENCODER0       = 0x04  # Encoder 0 tick count
TELEM_STEPPER0       = 0x05  # Stepper motor 0 state
TELEM_DC_MOTOR0      = 0x06  # DC motor 0 state

# Control telemetry sections
TELEM_CTRL_SIGNALS   = 0x10  # Control signal bus values
TELEM_CTRL_OBSERVERS = 0x11  # Observer state estimates
TELEM_CTRL_SLOTS     = 0x12  # Control slot status

__all__ = [
    "TELEM_IMU",
    "TELEM_ULTRASONIC",
    "TELEM_LIDAR",
    "TELEM_ENCODER0",
    "TELEM_STEPPER0",
    "TELEM_DC_MOTOR0",
    "TELEM_CTRL_SIGNALS",
    "TELEM_CTRL_OBSERVERS",
    "TELEM_CTRL_SLOTS",
]


# Section metadata for introspection
SECTION_INFO = {
    0x01: {
        "name": "TELEM_IMU",
        "description": "IMU sensor data (accel, gyro, temp)",
        "format": "online(u8) ok(u8) ax(i16) ay(i16) az(i16) gx(i16) gy(i16) gz(i16) temp(i16)",
        "size": 18,
    },
    0x02: {
        "name": "TELEM_ULTRASONIC",
        "description": "Ultrasonic distance sensor",
        "format": "sensor_id(u8) attached(u8) ok(u8) dist_mm(u16)",
        "size": 5,
    },
    0x03: {
        "name": "TELEM_LIDAR",
        "description": "LiDAR distance sensor",
        "format": "online(u8) ok(u8) dist_mm(u16) signal(u16)",
        "size": 6,
    },
    0x04: {
        "name": "TELEM_ENCODER0",
        "description": "Encoder 0 tick count",
        "format": "ticks(i32)",
        "size": 4,
    },
    0x05: {
        "name": "TELEM_STEPPER0",
        "description": "Stepper motor 0 state",
        "format": "motor_id(i8) attached(u8) enabled(u8) moving(u8) dir(u8) steps(i32) speed(i16)",
        "size": 11,
    },
    0x06: {
        "name": "TELEM_DC_MOTOR0",
        "description": "DC motor 0 state",
        "format": "attached(u8) speed_centi(i16)",
        "size": 3,
    },
    0x10: {
        "name": "TELEM_CTRL_SIGNALS",
        "description": "Control signal bus values",
        "format": "count(u16) [id(u16) value(f32) ts_ms(u32)]*",
        "size": None,
    },
    0x11: {
        "name": "TELEM_CTRL_OBSERVERS",
        "description": "Observer state estimates",
        "format": "slot_count(u8) [slot(u8) enabled(u8) num_states(u8) states(f32)*]*",
        "size": None,
    },
    0x12: {
        "name": "TELEM_CTRL_SLOTS",
        "description": "Control slot status",
        "format": "slot_count(u8) [slot(u8) enabled(u8) ok(u8) run_count(u32)]*",
        "size": None,
    },
}
