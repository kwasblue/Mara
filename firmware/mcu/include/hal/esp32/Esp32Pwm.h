#pragma once

#include "../IPwm.h"

namespace hal {

/// ESP32 PWM implementation using LEDC peripheral
class Esp32Pwm : public IPwm {
public:
    static constexpr uint8_t MAX_CHANNELS = 16;  // ESP32 has 16 LEDC channels

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
        bool attached = false;
    };
    ChannelConfig channels_[MAX_CHANNELS] = {};
};

} // namespace hal
