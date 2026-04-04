// include/hal/stubs/StubServo.h
// Stub servo implementation for native/test builds
#pragma once

#include "../IServo.h"

namespace hal {

class StubServo : public IServo {
public:
    uint8_t maxServos() const override { return 16; }

    bool attach(uint8_t servoId, uint8_t pin, uint16_t minUs = 500, uint16_t maxUs = 2500) override {
        (void)servoId; (void)pin; (void)minUs; (void)maxUs;
        return true;
    }

    void detach(uint8_t servoId) override { (void)servoId; }
    bool attached(uint8_t servoId) const override { (void)servoId; return false; }
    void write(uint8_t servoId, float angleDeg) override { (void)servoId; (void)angleDeg; }
    void writeMicroseconds(uint8_t servoId, uint16_t pulseUs) override { (void)servoId; (void)pulseUs; }
    float read(uint8_t servoId) const override { (void)servoId; return 0.0f; }
    uint16_t readMicroseconds(uint8_t servoId) const override { (void)servoId; return 1500; }
};

} // namespace hal
