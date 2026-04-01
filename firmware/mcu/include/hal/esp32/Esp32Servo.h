// include/hal/esp32/Esp32Servo.h
// ESP32 Servo implementation using ESP32Servo library (Arduino framework)
// or direct LEDC PWM control (ESP-IDF framework)
#pragma once

#include "../IServo.h"
#include "config/FeatureFlags.h"

#if HAS_SERVO

namespace hal {

/// ESP32 Servo implementation.
/// Uses the ESP32Servo library for Arduino framework, or can be adapted
/// for direct LEDC control under ESP-IDF.
class Esp32Servo : public IServo {
public:
    static constexpr uint8_t MAX_SERVOS = 16;  // ESP32 has 16 LEDC channels

    Esp32Servo();
    ~Esp32Servo() override;

    uint8_t maxServos() const override { return MAX_SERVOS; }

    bool attach(uint8_t servoId, uint8_t pin, uint16_t minUs = 500, uint16_t maxUs = 2500) override;
    void detach(uint8_t servoId) override;
    bool attached(uint8_t servoId) const override;

    void write(uint8_t servoId, float angleDeg) override;
    void writeMicroseconds(uint8_t servoId, uint16_t pulseUs) override;

    float read(uint8_t servoId) const override;
    uint16_t readMicroseconds(uint8_t servoId) const override;

private:
    struct ServoState {
        uint8_t pin = 255;
        uint16_t minUs = 500;
        uint16_t maxUs = 2500;
        uint16_t currentUs = 1500;  // Center position
        float currentAngle = 90.0f;
        bool isAttached = false;
        void* impl = nullptr;  // Platform-specific handle (Servo* for Arduino)
    };

    ServoState servos_[MAX_SERVOS];
};

} // namespace hal

#else // !HAS_SERVO

namespace hal {

/// Stub implementation when servo support is disabled
class Esp32Servo : public IServo {
public:
    uint8_t maxServos() const override { return 0; }
    bool attach(uint8_t, uint8_t, uint16_t = 500, uint16_t = 2500) override { return false; }
    void detach(uint8_t) override {}
    bool attached(uint8_t) const override { return false; }
    void write(uint8_t, float) override {}
    void writeMicroseconds(uint8_t, uint16_t) override {}
    float read(uint8_t) const override { return 0.0f; }
    uint16_t readMicroseconds(uint8_t) const override { return 1500; }
};

} // namespace hal

#endif // HAS_SERVO
