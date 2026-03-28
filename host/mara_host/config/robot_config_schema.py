# mara_host/config/robot_config_schema.py
"""
JSON Schema for robot configuration validation.

This schema validates robot YAML files at load time to catch errors early.
Uses JSON Schema Draft 2020-12.
"""

from typing import Any, Dict, List

# Transport configuration schema
TRANSPORT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["serial", "tcp", "ble"],
            "description": "Transport type for MCU communication",
        },
        "port": {
            "type": "string",
            "description": "Serial port path (e.g., /dev/ttyUSB0) or BLE device name",
        },
        "baudrate": {
            "type": "integer",
            "minimum": 9600,
            "maximum": 4000000,
            "default": 115200,
            "description": "Serial baud rate",
        },
        "host": {
            "type": "string",
            "description": "TCP host address",
        },
        "tcp_port": {
            "type": "integer",
            "minimum": 1,
            "maximum": 65535,
            "default": 3333,
            "description": "TCP port number",
        },
        "ble_name": {
            "type": "string",
            "description": "BLE device name to connect to",
        },
    },
    "allOf": [
        {
            "if": {"properties": {"type": {"const": "serial"}}},
            "then": {"required": ["port"]},
        },
        {
            "if": {"properties": {"type": {"const": "tcp"}}},
            "then": {"required": ["host"]},
        },
        {
            "if": {"properties": {"type": {"const": "ble"}}},
            "then": {
                "anyOf": [
                    {"required": ["ble_name"]},
                    {"required": ["port"]},
                ]
            },
        },
    ],
}

# Drive configuration schema
DRIVE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["differential", "ackermann", "mecanum", "omni"],
            "default": "differential",
            "description": "Drive kinematics type",
        },
        "wheel_radius": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Wheel radius in meters",
        },
        "wheel_base": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Distance between wheels in meters",
        },
        "max_linear_vel": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Maximum linear velocity in m/s",
        },
        "max_angular_vel": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Maximum angular velocity in rad/s",
        },
    },
}

# Features configuration schema
FEATURES_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "telemetry": {"type": "boolean", "default": True},
        "encoder": {"type": "boolean", "default": False},
        "motion": {"type": "boolean", "default": False},
        "modes": {"type": "boolean", "default": False},
        "camera": {"type": "boolean", "default": False},
    },
    "additionalProperties": {"type": "boolean"},
}

# Encoder defaults schema
ENCODER_DEFAULTS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "encoder_id": {
            "type": "integer",
            "minimum": 0,
            "default": 0,
        },
        "pin_a": {
            "type": "integer",
            "minimum": 0,
            "maximum": 39,
        },
        "pin_b": {
            "type": "integer",
            "minimum": 0,
            "maximum": 39,
        },
        "counts_per_rev": {
            "type": "integer",
            "exclusiveMinimum": 0,
        },
    },
}

# Settings configuration schema
SETTINGS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "telemetry_interval_ms": {
            "type": "integer",
            "minimum": 10,
            "maximum": 10000,
            "default": 100,
            "description": "Telemetry publish interval in milliseconds",
        },
        "pwm_freq_hz": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 100000,
            "default": 1000,
            "description": "PWM frequency in Hz",
        },
        "control_rate_hz": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 1000,
            "default": 50,
            "description": "Control loop rate in Hz",
        },
    },
}

# Sensor degradation configuration schema
SENSOR_DEGRADATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "required": {
            "type": "boolean",
            "default": False,
            "description": "Whether sensor is required for operation",
        },
        "allow_missing": {
            "type": "boolean",
            "default": True,
            "description": "Allow operation if sensor not present",
        },
        "stale_after_ms": {
            "type": "integer",
            "exclusiveMinimum": 0,
            "description": "Mark sensor stale after this many ms without update",
        },
        "fail_open": {
            "type": "boolean",
            "default": True,
            "description": "Continue operation on sensor failure",
        },
        "fallback": {
            "type": "string",
            "enum": ["none", "last_value", "default", "interpolate"],
            "default": "none",
            "description": "Fallback behavior when sensor fails",
        },
    },
}

# Individual sensor configuration schema
SENSOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "description": "Sensor type (e.g., imu, ultrasonic, encoder, lidar)",
        },
        "type": {
            "type": "string",
            "description": "Alias for kind",
        },
        "enabled": {
            "type": "boolean",
            "default": True,
        },
        "sensor_id": {
            "type": "integer",
            "minimum": 0,
            "default": 0,
        },
        "transport": {
            "type": "string",
            "enum": ["telemetry", "command", "service"],
            "default": "telemetry",
        },
        "topic": {
            "type": "string",
            "description": "Telemetry topic for this sensor",
        },
        "degradation": SENSOR_DEGRADATION_SCHEMA,
    },
    "additionalProperties": True,  # Allow pin configs and other sensor-specific fields
}

# Joint configuration schema (for robot definitions)
JOINT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["actuator", "actuator_id"],
    "properties": {
        "type": {
            "type": "string",
            "enum": ["revolute", "prismatic", "continuous"],
            "default": "revolute",
        },
        "actuator": {
            "type": "string",
            "enum": ["servo", "dc_motor", "stepper"],
        },
        "actuator_id": {
            "type": "integer",
            "minimum": 0,
        },
        "pin": {
            "type": "integer",
            "minimum": 0,
            "maximum": 39,
        },
        "min_angle": {"type": "number"},
        "max_angle": {"type": "number"},
        "home": {"type": "number"},
        "max_velocity": {
            "type": "number",
            "exclusiveMinimum": 0,
        },
        "zero_position": {"type": "string"},
        "max_position": {"type": "string"},
        "parent": {"type": "string"},
    },
}

# Main robot configuration schema
ROBOT_CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://mara.dev/schemas/robot-config.json",
    "title": "MARA Robot Configuration",
    "description": "Schema for MARA robot YAML configuration files",
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_-]*$",
            "description": "Robot name/identifier (alphanumeric, underscores, hyphens)",
        },
        "description": {
            "type": "string",
            "description": "Human-readable description of the robot",
        },
        "type": {
            "type": "string",
            "description": "Robot type (e.g., mobile_base, manipulator, test_platform)",
        },
        "transport": TRANSPORT_SCHEMA,
        "drive": DRIVE_SCHEMA,
        "features": FEATURES_SCHEMA,
        "encoder_defaults": ENCODER_DEFAULTS_SCHEMA,
        "settings": SETTINGS_SCHEMA,
        "sensors": {
            "type": "object",
            "additionalProperties": SENSOR_SCHEMA,
            "description": "Named sensor configurations",
        },
        "joints": {
            "type": "object",
            "additionalProperties": JOINT_SCHEMA,
            "description": "Named joint configurations",
        },
        "chains": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"},
            },
            "description": "Kinematic chains (ordered joint sequences)",
        },
        "groups": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"},
            },
            "description": "Joint groups for coordinated control",
        },
        "components": {
            "type": "object",
            "description": "Custom component configurations",
        },
    },
}


def validate_config_with_context(data: Dict[str, Any]) -> List[str]:
    """
    Validate config and return list of human-readable errors.

    Args:
        data: Configuration dictionary to validate

    Returns:
        List of error messages (empty if valid)
    """
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        # jsonschema not installed, skip validation
        return []

    validator = Draft202012Validator(ROBOT_CONFIG_SCHEMA)
    errors = []

    for error in validator.iter_errors(data):
        path = " -> ".join(str(p) for p in error.absolute_path)
        if path:
            errors.append(f"{path}: {error.message}")
        else:
            errors.append(error.message)

    return errors


class ConfigValidationError(Exception):
    """Raised when robot config fails schema validation."""

    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []


__all__ = [
    "ROBOT_CONFIG_SCHEMA",
    "TRANSPORT_SCHEMA",
    "DRIVE_SCHEMA",
    "FEATURES_SCHEMA",
    "SETTINGS_SCHEMA",
    "SENSOR_SCHEMA",
    "JOINT_SCHEMA",
    "validate_config_with_context",
    "ConfigValidationError",
]
