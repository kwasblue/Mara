// include/hal/linux/LinuxServo.h
// Linux servo implementation
//
// Uses either:
// 1. LinuxPwm (sysfs PWM) for hardware PWM pins
// 2. PCA9685 I2C servo driver for more channels
#pragma once

#include "../IServo.h"
#include <cstdint>
#include <array>

namespace hal {

// Forward declarations
class LinuxPwm;
class LinuxI2c;

/// Linux servo implementation
///
/// Servos are controlled via PWM signals:
/// - Period: typically 20ms (50Hz)
/// - Pulse width: 500-2500us maps to 0-180 degrees
///
/// This implementation supports:
/// - Hardware PWM via LinuxPwm (for GPIO-based servos)
/// - PCA9685 I2C PWM driver (for multiple servos)
class LinuxServo : public IServo {
public:
    /// Constructor for software/PCA9685 mode
    LinuxServo();

    /// Constructor with PWM backend
    /// @param pwm Pointer to LinuxPwm instance
    explicit LinuxServo(LinuxPwm* pwm);

    /// Constructor with I2C backend (PCA9685)
    /// @param i2c Pointer to LinuxI2c instance
    /// @param pca9685Address I2C address of PCA9685 (default: 0x40)
    LinuxServo(LinuxI2c* i2c, uint8_t pca9685Address = 0x40);

    ~LinuxServo() = default;

    uint8_t maxServos() const override;
    bool attach(uint8_t servoId, uint8_t pin, uint16_t minUs = 500, uint16_t maxUs = 2500) override;
    void detach(uint8_t servoId) override;
    bool attached(uint8_t servoId) const override;
    void write(uint8_t servoId, float angleDeg) override;
    void writeMicroseconds(uint8_t servoId, uint16_t pulseUs) override;
    float read(uint8_t servoId) const override;
    uint16_t readMicroseconds(uint8_t servoId) const override;

    /// Initialize PCA9685 if using I2C backend
    bool initPCA9685();

private:
    static constexpr uint8_t MAX_SERVOS = 16;
    static constexpr uint32_t SERVO_FREQ_HZ = 50;  // 50Hz = 20ms period
    static constexpr uint32_t PERIOD_US = 20000;   // 20ms

    struct ServoState {
        bool attached = false;
        uint8_t pin = 0;
        uint16_t minUs = 500;
        uint16_t maxUs = 2500;
        uint16_t currentUs = 1500;  // Center position
        float currentAngle = 90.0f;
    };

    enum class Backend {
        None,
        PWM,      // Hardware PWM via sysfs
        PCA9685   // I2C PWM driver
    };

    Backend backend_ = Backend::None;
    LinuxPwm* pwm_ = nullptr;
    LinuxI2c* i2c_ = nullptr;
    uint8_t pca9685Address_ = 0x40;
    std::array<ServoState, MAX_SERVOS> servos_;

    void setPwmPulse(uint8_t servoId, uint16_t pulseUs);
    bool writePCA9685Reg(uint8_t reg, uint8_t value);
    uint16_t angleToPulse(uint8_t servoId, float angleDeg) const;
    float pulseToAngle(uint8_t servoId, uint16_t pulseUs) const;
};

} // namespace hal
