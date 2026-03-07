#include "hal/esp32/Esp32Pwm.h"
#include <Arduino.h>

namespace hal {

bool Esp32Pwm::attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution) {
    if (channel >= MAX_CHANNELS) return false;
    if (resolution < 1 || resolution > 16) return false;

    // Setup LEDC channel
    ledcSetup(channel, frequency, resolution);
    ledcAttachPin(pin, channel);

    channels_[channel].pin = pin;
    channels_[channel].frequency = frequency;
    channels_[channel].resolution = resolution;
    channels_[channel].attached = true;

    return true;
}

void Esp32Pwm::detach(uint8_t channel) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    ledcDetachPin(channels_[channel].pin);
    channels_[channel].attached = false;
    channels_[channel].pin = 255;
}

void Esp32Pwm::setDuty(uint8_t channel, float duty) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    // Clamp duty to 0.0-1.0
    if (duty < 0.0f) duty = 0.0f;
    if (duty > 1.0f) duty = 1.0f;

    uint32_t maxValue = (1 << channels_[channel].resolution) - 1;
    uint32_t rawValue = (uint32_t)(duty * maxValue);
    ledcWrite(channel, rawValue);
}

void Esp32Pwm::setDutyRaw(uint8_t channel, uint32_t value) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    ledcWrite(channel, value);
}

void Esp32Pwm::setFrequency(uint8_t channel, uint32_t frequency) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    ledcWriteTone(channel, frequency);
    channels_[channel].frequency = frequency;
}

uint32_t Esp32Pwm::getFrequency(uint8_t channel) {
    if (channel >= MAX_CHANNELS) return 0;
    return channels_[channel].frequency;
}

uint8_t Esp32Pwm::getResolution(uint8_t channel) {
    if (channel >= MAX_CHANNELS) return 0;
    return channels_[channel].resolution;
}

} // namespace hal
