#pragma once

#include <cstdint>

namespace hal {

/// GPIO pin modes
enum class PinMode : uint8_t {
    Input,
    Output,
    InputPullup,
    InputPulldown,
    OpenDrain
};

/// Interrupt trigger modes
enum class InterruptMode : uint8_t {
    Disabled,
    Rising,
    Falling,
    Change,
    Low,
    High
};

/// Abstract GPIO interface for platform portability
class IGpio {
public:
    virtual ~IGpio() = default;

    /// Configure a pin's mode
    virtual void pinMode(uint8_t pin, PinMode mode) = 0;

    /// Write digital value (0 or 1)
    virtual void digitalWrite(uint8_t pin, uint8_t value) = 0;

    /// Read digital value (0 or 1)
    virtual int digitalRead(uint8_t pin) = 0;

    /// Toggle pin state (only valid for output pins)
    virtual void toggle(uint8_t pin) = 0;

    /// Attach interrupt to pin
    /// @param isr Interrupt service routine (must be IRAM_ATTR on ESP32)
    /// @param mode Trigger mode
    virtual void attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) = 0;

    /// Detach interrupt from pin
    virtual void detachInterrupt(uint8_t pin) = 0;

    /// Disable all interrupts (for critical sections)
    virtual void disableInterrupts() = 0;

    /// Re-enable interrupts (after critical section)
    virtual void enableInterrupts() = 0;
};

} // namespace hal
