#include "hal/esp32/Esp32Gpio.h"
#include <Arduino.h>

namespace hal {

void Esp32Gpio::pinMode(uint8_t pin, PinMode mode) {
    uint8_t arduinoMode;
    switch (mode) {
        case PinMode::Input:        arduinoMode = INPUT; break;
        case PinMode::Output:       arduinoMode = OUTPUT; break;
        case PinMode::InputPullup:  arduinoMode = INPUT_PULLUP; break;
        case PinMode::InputPulldown: arduinoMode = INPUT_PULLDOWN; break;
        case PinMode::OpenDrain:    arduinoMode = OUTPUT_OPEN_DRAIN; break;
        default:                    arduinoMode = INPUT; break;
    }
    ::pinMode(pin, arduinoMode);
}

void Esp32Gpio::digitalWrite(uint8_t pin, uint8_t value) {
    ::digitalWrite(pin, value);

    // Track state for toggle (bounds check: shifting by >= 64 is UB)
    if (pin < 64) {
        if (value) {
            outputStates_ |= (1ULL << pin);
        } else {
            outputStates_ &= ~(1ULL << pin);
        }
    }
}

int Esp32Gpio::digitalRead(uint8_t pin) {
    return ::digitalRead(pin);
}

void Esp32Gpio::toggle(uint8_t pin) {
    // NOTE: outputStates_ only tracks writes made through Esp32Gpio::digitalWrite.
    // If the pin was set by ::digitalWrite directly, another HAL instance, or by
    // stepper/PWM managers calling GPIO directly, outputStates_ will be stale and
    // toggle will flip to the wrong state. This HAL must be the exclusive writer
    // for all pins it tracks via toggle().
    if (pin >= 64) {
        return;  // Out of range for outputStates_ tracking
    }
    uint8_t newState = (outputStates_ & (1ULL << pin)) ? LOW : HIGH;
    digitalWrite(pin, newState);
}

void Esp32Gpio::attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) {
    int arduinoMode;
    switch (mode) {
        case InterruptMode::Rising:  arduinoMode = RISING; break;
        case InterruptMode::Falling: arduinoMode = FALLING; break;
        case InterruptMode::Change:  arduinoMode = CHANGE; break;
        case InterruptMode::Low:     arduinoMode = LOW; break;
        case InterruptMode::High:    arduinoMode = HIGH; break;
        default: return;
    }
    ::attachInterrupt(digitalPinToInterrupt(pin), isr, arduinoMode);
}

void Esp32Gpio::detachInterrupt(uint8_t pin) {
    ::detachInterrupt(digitalPinToInterrupt(pin));
}

void Esp32Gpio::disableInterrupts() {
    noInterrupts();
}

void Esp32Gpio::enableInterrupts() {
    interrupts();
}

} // namespace hal
