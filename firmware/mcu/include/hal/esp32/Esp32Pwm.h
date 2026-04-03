#pragma once

#include "../IPwm.h"
#include <cstdint>

namespace hal {

/// ESP32 PWM implementation using the LEDC peripheral.
/// Implementation uses ESP-IDF driver internally but header remains framework-agnostic.
class Esp32Pwm : public IPwm {
public:
    static constexpr uint8_t MAX_CHANNELS = 8;

    bool attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution = 12) override;
    void detach(uint8_t channel) override;
    void setDuty(uint8_t channel, float duty) override;
    void setDutyRaw(uint8_t channel, uint32_t value) override;
    void setFrequency(uint8_t channel, uint32_t frequency) override;
    uint32_t getFrequency(uint8_t channel) override;
    uint8_t getResolution(uint8_t channel) override;
    uint8_t maxChannels() const override { return MAX_CHANNELS; }

private:
    struct ChannelConfig {
        uint8_t pin = 255;
        uint8_t resolution = 0;
        uint32_t frequency = 0;
        uint32_t currentDuty = 0;
        uint8_t timerIndex = 0;  // Framework-agnostic timer index
        bool attached = false;
    };
    ChannelConfig channels_[MAX_CHANNELS] = {};
};

} // namespace hal
