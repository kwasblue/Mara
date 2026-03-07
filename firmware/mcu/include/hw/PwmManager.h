#pragma once

#include "hal/IPwm.h"
#include "core/Debug.h"
#include <map>

/// Channel-based PWM manager using HAL abstraction
/// Maps logical channels to HAL PWM channels
class PwmManager {
public:
    /// Set the HAL PWM driver (must be called before use)
    void setHal(hal::IPwm* pwm) {
        hal_ = pwm;
    }

    void registerChannel(int ch, int pin, int ledcChannel, float defaultFreq = 50.0f) {
        if (!hal_) {
            DBG_PRINTLN("[PWM] registerChannel: HAL not set!");
            return;
        }

        channelToLedc_[ch] = ledcChannel;
        freqDefault_[ch] = defaultFreq;

        // Use HAL to attach PWM channel (12-bit resolution)
        bool ok = hal_->attach(static_cast<uint8_t>(ledcChannel),
                               static_cast<uint8_t>(pin),
                               static_cast<uint32_t>(defaultFreq),
                               12);

        if (ok) {
            DBG_PRINTF("[PWM] registerChannel: ch=%d pin=%d ledcCH=%d freq=%.1f\n",
                       ch, pin, ledcChannel, defaultFreq);
        } else {
            DBG_PRINTF("[PWM] registerChannel FAILED: ch=%d\n", ch);
        }
    }

    void set(int ch, float duty, float freq = 0.0f) {
        if (!exists(ch)) return;
        if (!hal_) return;

        int ledcCH = channelToLedc_[ch];

        if (freq > 0.0f) {
            hal_->setFrequency(static_cast<uint8_t>(ledcCH),
                               static_cast<uint32_t>(freq));
            DBG_PRINTF("[PWM] set: ch=%d freq override=%.1f\n", ch, freq);
        }

        hal_->setDuty(static_cast<uint8_t>(ledcCH), duty);

        DBG_PRINTF("[PWM] set: ch=%d duty=%.3f\n", ch, duty);
    }

private:
    bool exists(int ch) {
        if (!channelToLedc_.count(ch)) {
            DBG_PRINTF("[PWM] Unknown channel %d\n", ch);
            return false;
        }
        return true;
    }

    hal::IPwm* hal_ = nullptr;
    std::map<int, int> channelToLedc_;
    std::map<int, float> freqDefault_;
};
