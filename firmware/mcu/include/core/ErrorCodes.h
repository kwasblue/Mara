#pragma once

#include <cstdint>

/**
 * Standard error codes for host/firmware communication.
 * Must stay in sync with host/mara_host/tools/schema/error_codes.py
 */
enum class ErrorCode : uint16_t {
    // Success (0)
    OK = 0,

    // General errors (1-99)
    UNKNOWN = 1,
    TIMEOUT = 2,
    CANCELLED = 3,
    NOT_IMPLEMENTED = 4,
    INVALID_PARAMETER = 5,
    INVALID_STATE = 6,
    RESOURCE_BUSY = 7,
    RESOURCE_NOT_FOUND = 8,

    // State machine errors (100-199)
    INVALID_TRANSITION = 100,
    NOT_ARMED = 101,
    NOT_ACTIVE = 102,
    IN_ESTOP = 103,
    CANNOT_CLEAR_ESTOP = 104,
    UNAUTHORIZED = 105,         // Missing or invalid signature for state transition
    SESSION_OCCUPIED = 106,     // Another host owns the session

    // Hardware errors (200-299)
    HARDWARE_FAULT = 200,
    SENSOR_OFFLINE = 201,
    MOTOR_FAULT = 202,
    ENCODER_FAULT = 203,
    IMU_OFFLINE = 204,
    I2C_ERROR = 205,

    // Communication errors (300-399)
    PROTOCOL_ERROR = 300,
    CRC_MISMATCH = 301,
    FRAME_TOO_LARGE = 302,
    MALFORMED_PAYLOAD = 303,

    // Control errors (400-499)
    CONTROL_GRAPH_INVALID = 400,
    SLOT_NOT_FOUND = 401,
    TRANSFORM_ERROR = 402,
    SIGNAL_NOT_FOUND = 403,

    // Configuration errors (500-599)
    CONFIG_INVALID = 500,
    MISSING_REQUIRED_FIELD = 501,
    VALUE_OUT_OF_RANGE = 502,
};

/**
 * Convert error code to string for debugging/logging.
 */
inline const char* errorCodeToString(ErrorCode code) {
    switch (code) {
        case ErrorCode::OK: return "OK";
        case ErrorCode::UNKNOWN: return "UNKNOWN";
        case ErrorCode::TIMEOUT: return "TIMEOUT";
        case ErrorCode::CANCELLED: return "CANCELLED";
        case ErrorCode::NOT_IMPLEMENTED: return "NOT_IMPLEMENTED";
        case ErrorCode::INVALID_PARAMETER: return "INVALID_PARAMETER";
        case ErrorCode::INVALID_STATE: return "INVALID_STATE";
        case ErrorCode::RESOURCE_BUSY: return "RESOURCE_BUSY";
        case ErrorCode::RESOURCE_NOT_FOUND: return "RESOURCE_NOT_FOUND";
        case ErrorCode::INVALID_TRANSITION: return "INVALID_TRANSITION";
        case ErrorCode::NOT_ARMED: return "NOT_ARMED";
        case ErrorCode::NOT_ACTIVE: return "NOT_ACTIVE";
        case ErrorCode::IN_ESTOP: return "IN_ESTOP";
        case ErrorCode::CANNOT_CLEAR_ESTOP: return "CANNOT_CLEAR_ESTOP";
        case ErrorCode::UNAUTHORIZED: return "UNAUTHORIZED";
        case ErrorCode::SESSION_OCCUPIED: return "SESSION_OCCUPIED";
        case ErrorCode::HARDWARE_FAULT: return "HARDWARE_FAULT";
        case ErrorCode::SENSOR_OFFLINE: return "SENSOR_OFFLINE";
        case ErrorCode::MOTOR_FAULT: return "MOTOR_FAULT";
        case ErrorCode::ENCODER_FAULT: return "ENCODER_FAULT";
        case ErrorCode::IMU_OFFLINE: return "IMU_OFFLINE";
        case ErrorCode::I2C_ERROR: return "I2C_ERROR";
        case ErrorCode::PROTOCOL_ERROR: return "PROTOCOL_ERROR";
        case ErrorCode::CRC_MISMATCH: return "CRC_MISMATCH";
        case ErrorCode::FRAME_TOO_LARGE: return "FRAME_TOO_LARGE";
        case ErrorCode::MALFORMED_PAYLOAD: return "MALFORMED_PAYLOAD";
        case ErrorCode::CONTROL_GRAPH_INVALID: return "CONTROL_GRAPH_INVALID";
        case ErrorCode::SLOT_NOT_FOUND: return "SLOT_NOT_FOUND";
        case ErrorCode::TRANSFORM_ERROR: return "TRANSFORM_ERROR";
        case ErrorCode::SIGNAL_NOT_FOUND: return "SIGNAL_NOT_FOUND";
        case ErrorCode::CONFIG_INVALID: return "CONFIG_INVALID";
        case ErrorCode::MISSING_REQUIRED_FIELD: return "MISSING_REQUIRED_FIELD";
        case ErrorCode::VALUE_OUT_OF_RANGE: return "VALUE_OUT_OF_RANGE";
        default: return "UNKNOWN";
    }
}
