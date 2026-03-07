#pragma once

#include "../IGpio.h"

namespace hal {

/// ESP32 GPIO implementation
class Esp32Gpio : public IGpio {
public:
    void pinMode(uint8_t pin, PinMode mode) override;
    void digitalWrite(uint8_t pin, uint8_t value) override;
    int digitalRead(uint8_t pin) override;
    void toggle(uint8_t pin) override;
    void attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) override;
    void detachInterrupt(uint8_t pin) override;
    void disableInterrupts() override;
    void enableInterrupts() override;

private:
    // Track output states for toggle
    uint64_t outputStates_ = 0;
};

} // namespace hal
