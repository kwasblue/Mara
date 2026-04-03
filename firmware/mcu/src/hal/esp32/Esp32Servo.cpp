// src/hal/esp32/Esp32Servo.cpp
// ESP32 Servo implementation

#include "hal/esp32/Esp32Servo.h"
#include "config/FeatureFlags.h"

#if HAS_SERVO

#include <ESP32Servo.h>  // Arduino ESP32Servo library

namespace hal {

Esp32Servo::Esp32Servo() {
    for (auto& s : servos_) {
        s = ServoState{};
    }
}

Esp32Servo::~Esp32Servo() {
    for (uint8_t i = 0; i < MAX_SERVOS; ++i) {
        if (servos_[i].isAttached) {
            detach(i);
        }
    }
}

bool Esp32Servo::attach(uint8_t servoId, uint8_t pin, uint16_t minUs, uint16_t maxUs) {
    if (servoId >= MAX_SERVOS) {
        return false;
    }

    // Detach if already attached
    if (servos_[servoId].isAttached) {
        detach(servoId);
    }

    // Create new Servo instance
    Servo* servo = new Servo();
    int ch = servo->attach(pin, minUs, maxUs);

    if (ch < 0) {
        delete servo;
        return false;
    }

    servos_[servoId].pin = pin;
    servos_[servoId].minUs = minUs;
    servos_[servoId].maxUs = maxUs;
    servos_[servoId].currentUs = (minUs + maxUs) / 2;
    servos_[servoId].currentAngle = 90.0f;
    servos_[servoId].isAttached = true;
    servos_[servoId].impl = servo;

    return true;
}

void Esp32Servo::detach(uint8_t servoId) {
    if (servoId >= MAX_SERVOS || !servos_[servoId].isAttached) {
        return;
    }

    Servo* servo = static_cast<Servo*>(servos_[servoId].impl);
    if (servo) {
        servo->detach();
        delete servo;
    }

    servos_[servoId].isAttached = false;
    servos_[servoId].impl = nullptr;
    servos_[servoId].pin = 255;
}

bool Esp32Servo::attached(uint8_t servoId) const {
    if (servoId >= MAX_SERVOS) {
        return false;
    }
    return servos_[servoId].isAttached;
}

void Esp32Servo::write(uint8_t servoId, float angleDeg) {
    if (servoId >= MAX_SERVOS || !servos_[servoId].isAttached) {
        return;
    }

    // Clamp angle to 0-180
    if (angleDeg < 0.0f) angleDeg = 0.0f;
    if (angleDeg > 180.0f) angleDeg = 180.0f;

    // Calculate pulse width from angle with full float precision
    // Using writeMicroseconds instead of write(int) to preserve sub-degree precision
    float ratio = angleDeg / 180.0f;
    uint16_t pulseUs = servos_[servoId].minUs +
        static_cast<uint16_t>(ratio * (servos_[servoId].maxUs - servos_[servoId].minUs));

    Servo* servo = static_cast<Servo*>(servos_[servoId].impl);
    if (servo) {
        servo->writeMicroseconds(pulseUs);
    }

    servos_[servoId].currentAngle = angleDeg;
    servos_[servoId].currentUs = pulseUs;
}

void Esp32Servo::writeMicroseconds(uint8_t servoId, uint16_t pulseUs) {
    if (servoId >= MAX_SERVOS || !servos_[servoId].isAttached) {
        return;
    }

    Servo* servo = static_cast<Servo*>(servos_[servoId].impl);
    if (servo) {
        servo->writeMicroseconds(pulseUs);
    }

    servos_[servoId].currentUs = pulseUs;

    // Calculate angle from pulse width
    float range = static_cast<float>(servos_[servoId].maxUs - servos_[servoId].minUs);
    float offset = static_cast<float>(pulseUs - servos_[servoId].minUs);
    servos_[servoId].currentAngle = (offset / range) * 180.0f;
}

float Esp32Servo::read(uint8_t servoId) const {
    if (servoId >= MAX_SERVOS) {
        return 0.0f;
    }
    return servos_[servoId].currentAngle;
}

uint16_t Esp32Servo::readMicroseconds(uint8_t servoId) const {
    if (servoId >= MAX_SERVOS) {
        return 1500;
    }
    return servos_[servoId].currentUs;
}

} // namespace hal

#endif // HAS_SERVO
