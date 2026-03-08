# schema/hardware/_sensors.py
"""
Sensor hardware definitions - SINGLE SOURCE OF TRUTH.

Adding a new sensor (3 steps):
    1. Add entry to SENSOR_HARDWARE below
    2. Run: mara generate all
    3. Implement firmware: Manager.h + Handler.h

That's it! Python host code and GUI are auto-generated.

Each sensor entry defines:
    - type: "sensor" (required)
    - interface: "i2c" | "gpio" | "uart" | "spi" | "adc"
    - gui: {label, color, outputs, inputs} - Block diagram appearance
    - commands: {CMD_NAME: {description, payload}} - Host → MCU commands
    - telemetry: {section, id, format, size, model} - MCU → Host data
    - firmware: {manager, handler, feature_flag} - Implementation hints

See docs/ADDING_HARDWARE.md for full guide.
"""

from typing import Any

SENSOR_HARDWARE: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # IMU - Inertial Measurement Unit
    # -------------------------------------------------------------------------
    "imu": {
        "type": "sensor",
        "interface": "i2c",
        "gui": {
            "label": "IMU",
            "color": "#22C55E",
            "outputs": [("accel", "Accel"), ("gyro", "Gyro")],
        },
        "commands": {
            "CMD_IMU_ATTACH": {
                "description": "Attach/configure IMU sensor",
                "payload": {
                    "i2c_addr": {"type": "int", "default": 0x68},
                },
            },
        },
        "telemetry": {
            "section": "TELEM_IMU",
            "id": 0x01,
            "description": "IMU sensor data (accel, gyro, temp)",
            "format": "online(u8) ok(u8) ax(i16) ay(i16) az(i16) gx(i16) gy(i16) gz(i16) temp(i16)",
            "size": 18,
            "model": {
                "name": "ImuTelemetry",
                "fields": [
                    ("online", "bool"),
                    ("ok", "bool"),
                    ("ax_g", "float", "ax * 0.001"),
                    ("ay_g", "float", "ay * 0.001"),
                    ("az_g", "float", "az * 0.001"),
                    ("gx_dps", "float", "gx * 0.001"),
                    ("gy_dps", "float", "gy * 0.001"),
                    ("gz_dps", "float", "gz * 0.001"),
                    ("temp_c", "float", "temp * 0.01"),
                ],
            },
        },
        "firmware": {
            "manager": "ImuManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_IMU",
        },
    },

    # -------------------------------------------------------------------------
    # Ultrasonic Distance Sensor
    # -------------------------------------------------------------------------
    "ultrasonic": {
        "type": "sensor",
        "interface": "gpio",
        "gui": {
            "label": "Ultrasonic",
            "color": "#3B82F6",
            "inputs": [("trig", "TRIG")],
            "outputs": [("echo", "ECHO")],
        },
        "commands": {
            "CMD_ULTRASONIC_ATTACH": {
                "description": "Attach/configure an ultrasonic sensor",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                },
            },
            "CMD_ULTRASONIC_READ": {
                "description": "Trigger a single ultrasonic distance measurement",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                },
            },
        },
        "telemetry": {
            "section": "TELEM_ULTRASONIC",
            "id": 0x02,
            "description": "Ultrasonic distance sensor",
            "format": "sensor_id(u8) attached(u8) ok(u8) dist_mm(u16)",
            "size": 5,
            "model": {
                "name": "UltrasonicTelemetry",
                "fields": [
                    ("sensor_id", "int"),
                    ("attached", "bool"),
                    ("ok", "bool"),
                    ("distance_cm", "float | None", "dist_mm * 0.1 if dist_mm else None"),
                    ("ts_ms", "int"),
                ],
            },
        },
        "firmware": {
            "manager": "UltrasonicManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_ULTRASONIC",
        },
    },

    # -------------------------------------------------------------------------
    # LiDAR Distance Sensor
    # -------------------------------------------------------------------------
    "lidar": {
        "type": "sensor",
        "interface": "uart",
        "gui": {
            "label": "LiDAR",
            "color": "#8B5CF6",
            "outputs": [("dist", "DIST")],
        },
        "commands": {
            "CMD_LIDAR_ATTACH": {
                "description": "Attach/configure LiDAR sensor",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                },
            },
        },
        "telemetry": {
            "section": "TELEM_LIDAR",
            "id": 0x03,
            "description": "LiDAR distance sensor",
            "format": "online(u8) ok(u8) dist_mm(u16) signal(u16)",
            "size": 6,
            "model": {
                "name": "LidarTelemetry",
                "fields": [
                    ("online", "bool"),
                    ("ok", "bool"),
                    ("distance_m", "float | None", "dist_mm * 0.001 if dist_mm else None"),
                    ("signal", "int | None", "signal if signal else None"),
                    ("ts_ms", "int"),
                ],
            },
        },
        "firmware": {
            "manager": "LidarManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_LIDAR",
        },
    },

    # -------------------------------------------------------------------------
    # Temperature Sensor (I2C)
    # -------------------------------------------------------------------------
    "temp": {
        "type": "sensor",
        "interface": "i2c",
        "gui": {
            "label": "Temperature",
            "color": "#F59E0B",
            "outputs": [("temp", "TEMP")],
        },
        "commands": {
            "CMD_TEMP_ATTACH": {
                "description": "Attach a temperature sensor",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                    "i2c_addr": {"type": "int", "default": 0x48},
                },
            },
            "CMD_TEMP_READ": {
                "description": "Read temperature from sensor",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                },
            },
        },
        "telemetry": {
            "section": "TELEM_TEMP",
            "id": 0x08,
            "description": "Temperature sensor reading",
            "format": "sensor_id(u8) ok(u8) temp_centi(i16)",
            "size": 4,
            "model": {
                "name": "TemperatureTelemetry",
                "fields": [
                    ("sensor_id", "int"),
                    ("ok", "bool"),
                    ("temp_c", "float", "temp_centi * 0.01"),
                    ("ts_ms", "int"),
                ],
            },
        },
        "firmware": {
            "manager": "TemperatureManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_TEMP_SENSOR",
        },
    },

    # -------------------------------------------------------------------------
    # IR Sensor (ADC)
    # -------------------------------------------------------------------------
    "ir": {
        "type": "sensor",
        "interface": "adc",
        "gui": {
            "label": "IR Sensor",
            "color": "#EF4444",
            "outputs": [("out", "OUT")],
        },
        "commands": {
            "CMD_IR_ATTACH": {
                "description": "Attach IR sensor",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                    "adc_pin": {"type": "int", "required": True},
                },
            },
            "CMD_IR_READ": {
                "description": "Read IR sensor value",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                },
            },
        },
        "telemetry": {
            "section": "TELEM_IR",
            "id": 0x09,
            "description": "IR sensor reading",
            "format": "sensor_id(u8) ok(u8) value(u16)",
            "size": 4,
            "model": {
                "name": "IrTelemetry",
                "fields": [
                    ("sensor_id", "int"),
                    ("ok", "bool"),
                    ("value", "int"),
                    ("ts_ms", "int"),
                ],
            },
        },
        "firmware": {
            "manager": "IrSensorManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_IR_SENSOR",
        },
    },

    # -------------------------------------------------------------------------
    # Encoder
    # -------------------------------------------------------------------------
    "encoder": {
        "type": "sensor",
        "interface": "gpio",
        "gui": {
            "label": "Encoder",
            "color": "#8B5CF6",
            "outputs": [("A", "A"), ("B", "B")],
        },
        "commands": {
            "CMD_ENCODER_ATTACH": {
                "description": "Attach quadrature encoder",
                "payload": {
                    "encoder_id": {"type": "int", "default": 0},
                    "pin_a": {"type": "int", "required": True},
                    "pin_b": {"type": "int", "required": True},
                },
            },
            "CMD_ENCODER_READ": {
                "description": "Read encoder tick count",
                "payload": {
                    "encoder_id": {"type": "int", "default": 0},
                },
            },
            "CMD_ENCODER_RESET": {
                "description": "Reset encoder count to zero",
                "payload": {
                    "encoder_id": {"type": "int", "default": 0},
                },
            },
        },
        "telemetry": {
            "section": "TELEM_ENCODER0",
            "id": 0x04,
            "description": "Encoder tick count",
            "format": "ticks(i32)",
            "size": 4,
            "model": {
                "name": "EncoderTelemetry",
                "fields": [
                    ("encoder_id", "int"),
                    ("ticks", "int"),
                    ("ts_ms", "int"),
                ],
            },
        },
        "firmware": {
            "manager": "EncoderManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_ENCODER",
        },
    },
}
