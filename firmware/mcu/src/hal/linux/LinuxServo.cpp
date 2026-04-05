// src/hal/linux/LinuxServo.cpp
// Linux servo implementation using PWM or PCA9685 I2C driver

#include "hal/linux/LinuxServo.h"
#include "hal/linux/LinuxPwm.h"
#include "hal/linux/LinuxI2c.h"

#if PLATFORM_LINUX

#include <unistd.h>

namespace hal {

// PCA9685 registers
constexpr uint8_t PCA9685_MODE1 = 0x00;
constexpr uint8_t PCA9685_PRESCALE = 0xFE;
constexpr uint8_t PCA9685_LED0_ON_L = 0x06;

LinuxServo::LinuxServo() : backend_(Backend::None) {
    servos_.fill(ServoState{});
}

LinuxServo::LinuxServo(LinuxPwm* pwm) : backend_(Backend::PWM), pwm_(pwm) {
    servos_.fill(ServoState{});
}

LinuxServo::LinuxServo(LinuxI2c* i2c, uint8_t pca9685Address)
    : backend_(Backend::PCA9685), i2c_(i2c), pca9685Address_(pca9685Address) {
    servos_.fill(ServoState{});
}

uint8_t LinuxServo::maxServos() const {
    return MAX_SERVOS;
}

bool LinuxServo::attach(uint8_t servoId, uint8_t pin, uint16_t minUs, uint16_t maxUs) {
    if (servoId >= MAX_SERVOS) {
        return false;
    }

    ServoState& servo = servos_[servoId];
    servo.pin = pin;
    servo.minUs = minUs;
    servo.maxUs = maxUs;
    servo.currentUs = (minUs + maxUs) / 2;  // Center
    servo.currentAngle = 90.0f;
    servo.attached = true;

    // Initialize backend if needed
    if (backend_ == Backend::PWM && pwm_) {
        // Attach PWM at 50Hz for servo control
        return pwm_->attach(pin, pin, SERVO_FREQ_HZ, 12);
    } else if (backend_ == Backend::PCA9685 && i2c_) {
        // PCA9685 initialization done in initPCA9685()
        return true;
    }

    // Software/stub mode - always succeeds
    return true;
}

void LinuxServo::detach(uint8_t servoId) {
    if (servoId >= MAX_SERVOS) {
        return;
    }

    ServoState& servo = servos_[servoId];
    if (!servo.attached) {
        return;
    }

    if (backend_ == Backend::PWM && pwm_) {
        pwm_->detach(servo.pin);
    }

    servo.attached = false;
}

bool LinuxServo::attached(uint8_t servoId) const {
    if (servoId >= MAX_SERVOS) {
        return false;
    }
    return servos_[servoId].attached;
}

void LinuxServo::write(uint8_t servoId, float angleDeg) {
    if (servoId >= MAX_SERVOS || !servos_[servoId].attached) {
        return;
    }

    // Clamp angle to 0-180
    if (angleDeg < 0.0f) angleDeg = 0.0f;
    if (angleDeg > 180.0f) angleDeg = 180.0f;

    servos_[servoId].currentAngle = angleDeg;
    uint16_t pulseUs = angleToPulse(servoId, angleDeg);
    writeMicroseconds(servoId, pulseUs);
}

void LinuxServo::writeMicroseconds(uint8_t servoId, uint16_t pulseUs) {
    if (servoId >= MAX_SERVOS || !servos_[servoId].attached) {
        return;
    }

    ServoState& servo = servos_[servoId];

    // Clamp to configured range
    if (pulseUs < servo.minUs) pulseUs = servo.minUs;
    if (pulseUs > servo.maxUs) pulseUs = servo.maxUs;

    servo.currentUs = pulseUs;
    servo.currentAngle = pulseToAngle(servoId, pulseUs);

    setPwmPulse(servoId, pulseUs);
}

float LinuxServo::read(uint8_t servoId) const {
    if (servoId >= MAX_SERVOS) {
        return 0.0f;
    }
    return servos_[servoId].currentAngle;
}

uint16_t LinuxServo::readMicroseconds(uint8_t servoId) const {
    if (servoId >= MAX_SERVOS) {
        return 0;
    }
    return servos_[servoId].currentUs;
}

bool LinuxServo::initPCA9685() {
    if (backend_ != Backend::PCA9685 || !i2c_) {
        return false;
    }

    // Reset MODE1 register
    if (!writePCA9685Reg(PCA9685_MODE1, 0x00)) {
        return false;
    }

    // Set prescaler for 50Hz
    // prescale = round(osc_clock / (4096 * freq)) - 1
    // osc_clock = 25MHz, freq = 50Hz
    // prescale = round(25000000 / (4096 * 50)) - 1 = 121
    uint8_t prescale = 121;

    // Must be in sleep mode to set prescaler
    if (!writePCA9685Reg(PCA9685_MODE1, 0x10)) {  // Sleep
        return false;
    }
    if (!writePCA9685Reg(PCA9685_PRESCALE, prescale)) {
        return false;
    }
    if (!writePCA9685Reg(PCA9685_MODE1, 0x00)) {  // Wake
        return false;
    }

    // Wait for oscillator
    usleep(5000);

    // Enable auto-increment
    if (!writePCA9685Reg(PCA9685_MODE1, 0x20)) {
        return false;
    }

    return true;
}

void LinuxServo::setPwmPulse(uint8_t servoId, uint16_t pulseUs) {
    if (backend_ == Backend::PWM && pwm_) {
        // Convert pulse width to duty cycle percentage
        // duty% = (pulseUs / periodUs) * 100
        float duty = (static_cast<float>(pulseUs) / PERIOD_US) * 100.0f;
        pwm_->setDuty(servos_[servoId].pin, duty);
    } else if (backend_ == Backend::PCA9685 && i2c_) {
        // PCA9685: 4096 counts per period
        // onTime = 0, offTime = (pulseUs / periodUs) * 4096
        uint16_t offTime = static_cast<uint16_t>((static_cast<uint32_t>(pulseUs) * 4096) / PERIOD_US);

        uint8_t reg = PCA9685_LED0_ON_L + 4 * servoId;
        uint8_t data[4] = {
            0x00,                           // ON_L
            0x00,                           // ON_H
            static_cast<uint8_t>(offTime & 0xFF),          // OFF_L
            static_cast<uint8_t>((offTime >> 8) & 0x0F)    // OFF_H
        };

        uint8_t pkt[5] = {reg, data[0], data[1], data[2], data[3]};
        i2c_->write(pca9685Address_, pkt, 5);
    }
    // Software mode: just store the value (already done in caller)
}

bool LinuxServo::writePCA9685Reg(uint8_t reg, uint8_t value) {
    if (!i2c_) {
        return false;
    }
    return i2c_->writeReg(pca9685Address_, reg, value) == I2cResult::Ok;
}

uint16_t LinuxServo::angleToPulse(uint8_t servoId, float angleDeg) const {
    const ServoState& servo = servos_[servoId];
    // Linear mapping from 0-180 degrees to minUs-maxUs
    return static_cast<uint16_t>(
        servo.minUs + (angleDeg / 180.0f) * (servo.maxUs - servo.minUs)
    );
}

float LinuxServo::pulseToAngle(uint8_t servoId, uint16_t pulseUs) const {
    const ServoState& servo = servos_[servoId];
    if (servo.maxUs == servo.minUs) {
        return 90.0f;
    }
    // Linear mapping from minUs-maxUs to 0-180 degrees
    return ((static_cast<float>(pulseUs) - servo.minUs) / (servo.maxUs - servo.minUs)) * 180.0f;
}

} // namespace hal

#endif // PLATFORM_LINUX
