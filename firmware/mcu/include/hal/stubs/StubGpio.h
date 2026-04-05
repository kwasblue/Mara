// include/hal/stubs/StubGpio.h
// Stub GPIO implementation for native/test builds
#pragma once

#include "../IGpio.h"

namespace hal {

class StubGpio : public IGpio {
public:
    void pinMode(uint8_t pin, PinMode mode) override { (void)pin; (void)mode; }
    void digitalWrite(uint8_t pin, uint8_t value) override { (void)pin; (void)value; }
    int  digitalRead(uint8_t pin) override { (void)pin; return 0; }
    void toggle(uint8_t pin) override { (void)pin; }
    void attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) override {
        (void)pin; (void)isr; (void)mode;
    }
    void detachInterrupt(uint8_t pin) override { (void)pin; }
    void disableInterrupts() override {}
    void enableInterrupts() override {}
};

} // namespace hal
