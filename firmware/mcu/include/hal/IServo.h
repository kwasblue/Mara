// include/hal/IServo.h
// Abstract servo motor interface for platform portability.
// Wraps platform-specific servo libraries (ESP32Servo, STM32 Servo, etc.)
#pragma once

#include <cstdint>

namespace hal {

/// Abstract servo motor interface.
/// Platform implementations wrap ESP32Servo, Arduino Servo, or direct PWM.
///
/// Servos use pulse-width modulation to control position:
/// - Typical range: 500us (0 deg) to 2500us (180 deg)
/// - Standard range: 1000us (0 deg) to 2000us (180 deg)
///
/// Usage:
///   IServo* servo = hal.servo;
///   servo->attach(0, 13, 500, 2500);  // Servo 0 on pin 13
///   servo->write(0, 90.0f);           // Move to 90 degrees
class IServo {
public:
    virtual ~IServo() = default;

    /// Maximum number of servos supported
    virtual uint8_t maxServos() const = 0;

    /// Attach a servo to a pin
    /// @param servoId Logical servo ID (0 to maxServos-1)
    /// @param pin GPIO pin number
    /// @param minUs Minimum pulse width in microseconds (default: 500)
    /// @param maxUs Maximum pulse width in microseconds (default: 2500)
    /// @return true if successful
    virtual bool attach(uint8_t servoId, uint8_t pin, uint16_t minUs = 500, uint16_t maxUs = 2500) = 0;

    /// Detach a servo
    /// @param servoId Servo ID to detach
    virtual void detach(uint8_t servoId) = 0;

    /// Check if a servo is attached
    /// @param servoId Servo ID to check
    /// @return true if attached
    virtual bool attached(uint8_t servoId) const = 0;

    /// Write angle to servo
    /// @param servoId Servo ID
    /// @param angleDeg Angle in degrees (0-180)
    virtual void write(uint8_t servoId, float angleDeg) = 0;

    /// Write raw pulse width to servo
    /// @param servoId Servo ID
    /// @param pulseUs Pulse width in microseconds
    virtual void writeMicroseconds(uint8_t servoId, uint16_t pulseUs) = 0;

    /// Read current angle
    /// @param servoId Servo ID
    /// @return Last written angle in degrees
    virtual float read(uint8_t servoId) const = 0;

    /// Read current pulse width
    /// @param servoId Servo ID
    /// @return Last written pulse width in microseconds
    virtual uint16_t readMicroseconds(uint8_t servoId) const = 0;
};

} // namespace hal
