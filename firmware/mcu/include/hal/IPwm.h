#pragma once

#include <cstdint>

namespace hal {

/// Abstract PWM interface for platform portability
class IPwm {
public:
    virtual ~IPwm() = default;

    /// Attach a PWM channel to a pin
    /// @param channel Logical channel number (0-15 on ESP32)
    /// @param pin GPIO pin number
    /// @param frequency Initial frequency in Hz
    /// @param resolution Bits of resolution (1-16, default 12)
    /// @return true if successful
    virtual bool attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution = 12) = 0;

    /// Detach PWM from channel
    virtual void detach(uint8_t channel) = 0;

    /// Set duty cycle
    /// @param channel PWM channel
    /// @param duty Duty cycle 0.0 to 1.0
    virtual void setDuty(uint8_t channel, float duty) = 0;

    /// Set duty cycle as raw value
    /// @param channel PWM channel
    /// @param value Raw duty value (0 to 2^resolution - 1)
    virtual void setDutyRaw(uint8_t channel, uint32_t value) = 0;

    /// Set frequency
    /// @param channel PWM channel
    /// @param frequency Frequency in Hz
    virtual void setFrequency(uint8_t channel, uint32_t frequency) = 0;

    /// Get current frequency
    virtual uint32_t getFrequency(uint8_t channel) = 0;

    /// Get resolution (bits)
    virtual uint8_t getResolution(uint8_t channel) = 0;

    /// Get maximum channels supported
    virtual uint8_t maxChannels() const = 0;
};

} // namespace hal
