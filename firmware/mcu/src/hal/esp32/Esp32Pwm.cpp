// ESP32 PWM implementation using ESP-IDF LEDC driver
// All ESP-IDF specifics are contained in this file - header remains framework-agnostic

#include "hal/esp32/Esp32Pwm.h"

// ESP-IDF includes (implementation detail, not exposed in header)
#include <driver/ledc.h>
#include <esp_err.h>

namespace hal {

// Internal helpers to convert framework-agnostic indices to ESP-IDF types
namespace {

inline ledc_channel_t toChannel(uint8_t ch) {
    return static_cast<ledc_channel_t>(ch);
}

inline ledc_timer_t toTimer(uint8_t ch) {
    // Map 2 channels per timer: ch 0-1 -> timer 0, ch 2-3 -> timer 1, etc.
    return static_cast<ledc_timer_t>(ch / 2);
}

} // anonymous namespace


bool Esp32Pwm::attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution) {
    if (channel >= MAX_CHANNELS) return false;
    if (resolution < 1 || resolution > 14) return false;  // ESP32 LEDC max is 14-bit

    ledc_timer_t timer = toTimer(channel);
    ledc_channel_t ledc_ch = toChannel(channel);

    // Configure timer
    ledc_timer_config_t timer_cfg = {};
    timer_cfg.speed_mode = LEDC_LOW_SPEED_MODE;
    timer_cfg.timer_num = timer;
    timer_cfg.duty_resolution = static_cast<ledc_timer_bit_t>(resolution);
    timer_cfg.freq_hz = frequency;
    timer_cfg.clk_cfg = LEDC_AUTO_CLK;

    esp_err_t err = ledc_timer_config(&timer_cfg);
    if (err != ESP_OK) {
        return false;
    }

    // Configure channel
    ledc_channel_config_t ch_cfg = {};
    ch_cfg.speed_mode = LEDC_LOW_SPEED_MODE;
    ch_cfg.channel = ledc_ch;
    ch_cfg.timer_sel = timer;
    ch_cfg.intr_type = LEDC_INTR_DISABLE;
    ch_cfg.gpio_num = pin;
    ch_cfg.duty = 0;
    ch_cfg.hpoint = 0;

    err = ledc_channel_config(&ch_cfg);
    if (err != ESP_OK) {
        return false;
    }

    channels_[channel].pin = pin;
    channels_[channel].frequency = frequency;
    channels_[channel].resolution = resolution;
    channels_[channel].timerIndex = static_cast<uint8_t>(timer);
    channels_[channel].currentDuty = 0;
    channels_[channel].attached = true;

    return true;
}

void Esp32Pwm::detach(uint8_t channel) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    ledc_channel_t ledc_ch = toChannel(channel);

    // Stop the channel (sets output low)
    ledc_stop(LEDC_LOW_SPEED_MODE, ledc_ch, 0);

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
    uint32_t rawValue = static_cast<uint32_t>(duty * maxValue);

    ledc_channel_t ledc_ch = toChannel(channel);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_ch, rawValue);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_ch);

    channels_[channel].currentDuty = rawValue;
}

void Esp32Pwm::setDutyRaw(uint8_t channel, uint32_t value) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    ledc_channel_t ledc_ch = toChannel(channel);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_ch, value);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_ch);

    channels_[channel].currentDuty = value;
}

void Esp32Pwm::setFrequency(uint8_t channel, uint32_t frequency) {
    if (channel >= MAX_CHANNELS) return;
    if (!channels_[channel].attached) return;

    ledc_timer_t timer = static_cast<ledc_timer_t>(channels_[channel].timerIndex);

    // ledc_set_freq changes frequency while preserving duty cycle ratio
    ledc_set_freq(LEDC_LOW_SPEED_MODE, timer, frequency);

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
