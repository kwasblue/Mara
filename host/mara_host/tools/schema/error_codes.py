# schema/error_codes.py
"""Error code definitions for structured error handling."""

from enum import IntEnum


class ErrorCode(IntEnum):
    """Standard error codes for host/firmware communication."""

    # Success (0)
    OK = 0

    # General errors (1-99)
    UNKNOWN = 1
    TIMEOUT = 2
    CANCELLED = 3
    NOT_IMPLEMENTED = 4
    INVALID_PARAMETER = 5
    INVALID_STATE = 6
    RESOURCE_BUSY = 7
    RESOURCE_NOT_FOUND = 8

    # State machine errors (100-199)
    INVALID_TRANSITION = 100
    NOT_ARMED = 101
    NOT_ACTIVE = 102
    IN_ESTOP = 103
    CANNOT_CLEAR_ESTOP = 104

    # Hardware errors (200-299)
    HARDWARE_FAULT = 200
    SENSOR_OFFLINE = 201
    MOTOR_FAULT = 202
    ENCODER_FAULT = 203
    IMU_OFFLINE = 204
    I2C_ERROR = 205

    # Communication errors (300-399)
    PROTOCOL_ERROR = 300
    CRC_MISMATCH = 301
    FRAME_TOO_LARGE = 302
    MALFORMED_PAYLOAD = 303

    # Control errors (400-499)
    CONTROL_GRAPH_INVALID = 400
    SLOT_NOT_FOUND = 401
    TRANSFORM_ERROR = 402
    SIGNAL_NOT_FOUND = 403

    # Configuration errors (500-599)
    CONFIG_INVALID = 500
    MISSING_REQUIRED_FIELD = 501
    VALUE_OUT_OF_RANGE = 502


# Error code to human-readable message mapping
ERROR_MESSAGES: dict[int, str] = {
    ErrorCode.OK: "Success",
    ErrorCode.UNKNOWN: "Unknown error",
    ErrorCode.TIMEOUT: "Operation timed out",
    ErrorCode.CANCELLED: "Operation cancelled",
    ErrorCode.NOT_IMPLEMENTED: "Not implemented",
    ErrorCode.INVALID_PARAMETER: "Invalid parameter",
    ErrorCode.INVALID_STATE: "Invalid state",
    ErrorCode.RESOURCE_BUSY: "Resource busy",
    ErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
    ErrorCode.INVALID_TRANSITION: "Invalid state transition",
    ErrorCode.NOT_ARMED: "Robot not armed",
    ErrorCode.NOT_ACTIVE: "Robot not active",
    ErrorCode.IN_ESTOP: "Emergency stop active",
    ErrorCode.CANNOT_CLEAR_ESTOP: "Cannot clear emergency stop",
    ErrorCode.HARDWARE_FAULT: "Hardware fault",
    ErrorCode.SENSOR_OFFLINE: "Sensor offline",
    ErrorCode.MOTOR_FAULT: "Motor fault",
    ErrorCode.ENCODER_FAULT: "Encoder fault",
    ErrorCode.IMU_OFFLINE: "IMU offline",
    ErrorCode.I2C_ERROR: "I2C communication error",
    ErrorCode.PROTOCOL_ERROR: "Protocol error",
    ErrorCode.CRC_MISMATCH: "CRC mismatch",
    ErrorCode.FRAME_TOO_LARGE: "Frame too large",
    ErrorCode.MALFORMED_PAYLOAD: "Malformed payload",
    ErrorCode.CONTROL_GRAPH_INVALID: "Invalid control graph",
    ErrorCode.SLOT_NOT_FOUND: "Slot not found",
    ErrorCode.TRANSFORM_ERROR: "Transform error",
    ErrorCode.SIGNAL_NOT_FOUND: "Signal not found",
    ErrorCode.CONFIG_INVALID: "Invalid configuration",
    ErrorCode.MISSING_REQUIRED_FIELD: "Missing required field",
    ErrorCode.VALUE_OUT_OF_RANGE: "Value out of range",
}


def get_error_message(code: int) -> str:
    """Get human-readable message for an error code."""
    return ERROR_MESSAGES.get(code, f"Unknown error code: {code}")
