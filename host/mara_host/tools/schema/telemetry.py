# schema/telemetry.py
"""Telemetry section definitions for binary telemetry packets."""

from typing import Dict, Any, Optional

# Section IDs for binary telemetry packets.
# Must match MCU registerBinProvider(section_id, ...) calls.

TELEMETRY_SECTIONS: Dict[str, Dict[str, Any]] = {
    "TELEM_IMU": {
        "id": 0x01,
        "description": "IMU sensor data (accel, gyro, temp)",
        "format": "online(u8) ok(u8) ax(i16) ay(i16) az(i16) gx(i16) gy(i16) gz(i16) temp(i16)",
        "size": 18,
    },
    "TELEM_ULTRASONIC": {
        "id": 0x02,
        "description": "Ultrasonic distance sensor",
        "format": "sensor_id(u8) attached(u8) ok(u8) dist_mm(u16)",
        "size": 5,
    },
    "TELEM_LIDAR": {
        "id": 0x03,
        "description": "LiDAR distance sensor",
        "format": "online(u8) ok(u8) dist_mm(u16) signal(u16)",
        "size": 6,
    },
    "TELEM_ENCODER0": {
        "id": 0x04,
        "description": "Encoder 0 tick count",
        "format": "ticks(i32)",
        "size": 4,
    },
    "TELEM_STEPPER0": {
        "id": 0x05,
        "description": "Stepper motor 0 state",
        "format": "motor_id(i8) attached(u8) enabled(u8) moving(u8) dir(u8) steps(i32) speed(i16)",
        "size": 11,
    },
    "TELEM_DC_MOTOR0": {
        "id": 0x06,
        "description": "DC motor 0 state",
        "format": "attached(u8) speed_centi(i16)",
        "size": 3,
    },
    "TELEM_CTRL_SIGNALS": {
        "id": 0x10,
        "description": "Control signal bus values",
        "format": "count(u16) [id(u16) value(f32) ts_ms(u32)]*",
        "size": None,  # Variable length
    },
    "TELEM_CTRL_OBSERVERS": {
        "id": 0x11,
        "description": "Observer state estimates",
        "format": "slot_count(u8) [slot(u8) enabled(u8) num_states(u8) states(f32)*]*",
        "size": None,  # Variable length
    },
    "TELEM_CTRL_SLOTS": {
        "id": 0x12,
        "description": "Control slot status",
        "format": "slot_count(u8) [slot(u8) enabled(u8) ok(u8) run_count(u32)]*",
        "size": None,  # Variable length
    },
}
