// include/hal/stubs/StubGpio.h
// Stub GPIO implementation for native/test builds
#pragma once

#include "../IGpio.h"

namespace hal {

class StubGpio : public IGpio {
public:
    void pinMode(uint8_t pin, PinMode mode) override { (void)pin; (void)mode; }
    void digitalWrite(uint8_t pin, bool value) override { (void)pin; (void)value; }
    bool digitalRead(uint8_t pin) override { (void)pin; return false; }
    uint16_t analogRead(uint8_t pin) override { (void)pin; return 0; }
    void attachInterrupt(uint8_t pin, InterruptCallback cb, InterruptMode mode) override {
        (void)pin; (void)cb; (void)mode;
    }
    void detachInterrupt(uint8_t pin) override { (void)pin; }
};

} // namespace hal
