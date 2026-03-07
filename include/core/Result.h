#pragma once

#include <cstdint>

namespace mara {

// =============================================================================
// ERROR MODEL DESIGN
// =============================================================================
//
// This codebase uses TWO complementary error models for different contexts:
//
// 1. ErrorCode (this file) - For INTERNAL service APIs
//    - Typed enum with domain-organized codes
//    - Used by: Result<T>, service methods, internal APIs
//    - Benefits: Compile-time safety, switch exhaustiveness, binary efficiency
//    - Example: MotorManager::attach() returns Result<void> with ErrorCode
//
// 2. const char* error - For COMMAND HANDLER responses
//    - Human-readable strings embedded in JSON responses
//    - Used by: Decoder result types (SlotConfigResult, etc.), JSON ACKs
//    - Benefits: Client-friendly, self-documenting, no error code table needed
//    - Example: {"type":"ACK","error":"missing_slot"} in JSON response
//
// WHY TWO MODELS?
//
// The boundary between internal code and external protocol requires translation:
//   - Internal: Type safety, performance, compile-time checks
//   - External: Human readability, protocol simplicity, client convenience
//
// Decoders sit at this boundary - they parse JSON (external) and produce
// results consumed by handlers (internal). Using string errors in decoders:
//   - Avoids adding JSON→ErrorCode mapping tables
//   - Lets handlers pass errors directly to JSON responses
//   - Keeps decoder logic simple and self-documenting
//
// WHEN TO USE WHICH:
//
//   | Context                    | Use                        |
//   |----------------------------|----------------------------|
//   | Service method return      | Result<T> with ErrorCode   |
//   | Internal error propagation | Result<T> with ErrorCode   |
//   | Decoder validation error   | const char* in result type |
//   | JSON ACK/NACK response     | const char* in JSON        |
//   | Logging/debugging          | errorCodeToString()        |
//
// CONVERSION:
//
//   ErrorCode → string: Use errorCodeToString(code)
//   string → ErrorCode: Not needed (each boundary handles its own model)
//
// =============================================================================

// Error codes organized by domain
// Generic:   0x0001 - 0x00FF
// Hardware:  0x0100 - 0x01FF
// Motor:     0x0200 - 0x02FF
// Sensor:    0x0300 - 0x03FF
// Command:   0x0400 - 0x04FF
// Safety:    0x0500 - 0x05FF
enum class ErrorCode : uint16_t {
    // Success
    Ok = 0,

    // Generic (0x0001-0x00FF)
    Unknown          = 0x0001,
    InvalidArgument  = 0x0002,
    OutOfRange       = 0x0003,
    NotInitialized   = 0x0004,
    AlreadyExists    = 0x0005,
    Timeout          = 0x0006,
    BufferFull       = 0x0007,
    NotFound         = 0x0008,
    NotSupported     = 0x0009,

    // Hardware (0x0100-0x01FF)
    HwGpioInvalid     = 0x0100,
    HwGpioNotOutput   = 0x0101,
    HwPwmAttachFailed = 0x0102,
    HwI2cTimeout      = 0x0103,
    HwI2cNack         = 0x0104,
    HwSpiError        = 0x0105,
    HwPinInUse        = 0x0106,

    // Motor (0x0200-0x02FF)
    MotorNotAttached   = 0x0200,
    MotorAlreadyAttach = 0x0201,
    MotorInvalidId     = 0x0202,
    MotorPidNotEnabled = 0x0203,
    MotorLimitExceeded = 0x0204,

    // Sensor (0x0300-0x03FF)
    SensorNotOnline   = 0x0300,
    SensorReadFailed  = 0x0301,
    SensorNotAttached = 0x0302,
    SensorInvalidId   = 0x0303,

    // Command (0x0400-0x04FF)
    CmdUnknown        = 0x0400,
    CmdMissingParam   = 0x0401,
    CmdInvalidParam   = 0x0402,
    CmdNotAllowed     = 0x0403,

    // Safety (0x0500-0x05FF)
    SafetyNotArmed     = 0x0500,
    SafetyEstopped     = 0x0501,
    SafetyNotConnected = 0x0502,
    SafetyVelExceeded  = 0x0503,
    SafetyTimeout      = 0x0504,
};

// Error code to string lookup (inline for header-only usage)
inline const char* errorCodeToString(ErrorCode code) {
    switch (code) {
        case ErrorCode::Ok:               return "Ok";
        case ErrorCode::Unknown:          return "Unknown";
        case ErrorCode::InvalidArgument:  return "InvalidArgument";
        case ErrorCode::OutOfRange:       return "OutOfRange";
        case ErrorCode::NotInitialized:   return "NotInitialized";
        case ErrorCode::AlreadyExists:    return "AlreadyExists";
        case ErrorCode::Timeout:          return "Timeout";
        case ErrorCode::BufferFull:       return "BufferFull";
        case ErrorCode::NotFound:         return "NotFound";
        case ErrorCode::NotSupported:     return "NotSupported";
        case ErrorCode::HwGpioInvalid:     return "HwGpioInvalid";
        case ErrorCode::HwGpioNotOutput:   return "HwGpioNotOutput";
        case ErrorCode::HwPwmAttachFailed: return "HwPwmAttachFailed";
        case ErrorCode::HwI2cTimeout:      return "HwI2cTimeout";
        case ErrorCode::HwI2cNack:         return "HwI2cNack";
        case ErrorCode::HwSpiError:        return "HwSpiError";
        case ErrorCode::HwPinInUse:        return "HwPinInUse";
        case ErrorCode::MotorNotAttached:   return "MotorNotAttached";
        case ErrorCode::MotorAlreadyAttach: return "MotorAlreadyAttach";
        case ErrorCode::MotorInvalidId:     return "MotorInvalidId";
        case ErrorCode::MotorPidNotEnabled: return "MotorPidNotEnabled";
        case ErrorCode::MotorLimitExceeded: return "MotorLimitExceeded";
        case ErrorCode::SensorNotOnline:   return "SensorNotOnline";
        case ErrorCode::SensorReadFailed:  return "SensorReadFailed";
        case ErrorCode::SensorNotAttached: return "SensorNotAttached";
        case ErrorCode::SensorInvalidId:   return "SensorInvalidId";
        case ErrorCode::CmdUnknown:       return "CmdUnknown";
        case ErrorCode::CmdMissingParam:  return "CmdMissingParam";
        case ErrorCode::CmdInvalidParam:  return "CmdInvalidParam";
        case ErrorCode::CmdNotAllowed:    return "CmdNotAllowed";
        case ErrorCode::SafetyNotArmed:     return "SafetyNotArmed";
        case ErrorCode::SafetyEstopped:     return "SafetyEstopped";
        case ErrorCode::SafetyNotConnected: return "SafetyNotConnected";
        case ErrorCode::SafetyVelExceeded:  return "SafetyVelExceeded";
        case ErrorCode::SafetyTimeout:      return "SafetyTimeout";
        default: return "UnknownError";
    }
}

// Result<T>: A value-or-error type (similar to Rust's Result or C++23 expected)
// Zero-overhead: no heap allocation, no exceptions
template<typename T>
class Result {
public:
    // Success constructor
    static Result ok(const T& value) {
        Result r;
        r.value_ = value;
        r.error_ = ErrorCode::Ok;
        return r;
    }

    static Result ok(T&& value) {
        Result r;
        r.value_ = static_cast<T&&>(value);
        r.error_ = ErrorCode::Ok;
        return r;
    }

    // Error constructor
    static Result err(ErrorCode code) {
        Result r;
        r.error_ = code;
        return r;
    }

    // Check state
    bool isOk() const { return error_ == ErrorCode::Ok; }
    bool isError() const { return error_ != ErrorCode::Ok; }
    explicit operator bool() const { return isOk(); }

    // Access value (undefined behavior if error)
    T& value() & { return value_; }
    const T& value() const& { return value_; }
    T&& value() && { return static_cast<T&&>(value_); }

    // Access error code
    ErrorCode error() const { return error_; }
    ErrorCode errorCode() const { return error_; }

    // Value with default fallback
    T valueOr(const T& defaultValue) const {
        return isOk() ? value_ : defaultValue;
    }

private:
    Result() = default;

    T value_{};
    ErrorCode error_ = ErrorCode::Unknown;
};

// Specialization for void (error-only result)
template<>
class Result<void> {
public:
    // Success constructor
    static Result ok() {
        Result r;
        r.error_ = ErrorCode::Ok;
        return r;
    }

    // Error constructor
    static Result err(ErrorCode code) {
        Result r;
        r.error_ = code;
        return r;
    }

    // Check state
    bool isOk() const { return error_ == ErrorCode::Ok; }
    bool isError() const { return error_ != ErrorCode::Ok; }
    explicit operator bool() const { return isOk(); }

    // Access error code
    ErrorCode error() const { return error_; }
    ErrorCode errorCode() const { return error_; }

private:
    Result() = default;
    ErrorCode error_ = ErrorCode::Unknown;
};

// Type alias for common use
using VoidResult = Result<void>;

// TRY macro: Early return on error
// Usage: TRY(someFunction()); // returns error if someFunction() fails
#define MCU_TRY(expr) \
    do { \
        auto _mcu_try_result = (expr); \
        if (_mcu_try_result.isError()) { \
            return ::mara::Result<void>::err(_mcu_try_result.errorCode()); \
        } \
    } while(0)

// TRY with value extraction
// Usage: auto val = TRY_VAL(someFunction()); // returns error or assigns value
#define MCU_TRY_VAL(var, expr) \
    auto _mcu_try_##var##_result = (expr); \
    if (_mcu_try_##var##_result.isError()) { \
        return ::mara::Result<decltype(var)>::err(_mcu_try_##var##_result.errorCode()); \
    } \
    var = _mcu_try_##var##_result.value()

// Convenience macros (shorter names, use with caution in headers)
#ifndef MCU_NO_SHORT_MACROS
#define TRY(expr) MCU_TRY(expr)
#endif

} // namespace mara
