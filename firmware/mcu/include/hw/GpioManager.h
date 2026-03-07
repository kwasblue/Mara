#pragma once

#include "hal/IGpio.h"
#include "core/Debug.h"

/// Channel-based GPIO manager using HAL abstraction
/// Maps logical channels (0-15) to physical pins
class GpioManager {
public:
    static constexpr int MAX_CHANNELS = 16;

    GpioManager() {
        for (int i = 0; i < MAX_CHANNELS; ++i) {
            pinForChannel_[i] = -1;
        }
    }

    /// Set the HAL GPIO driver (must be called before use)
    void setHal(hal::IGpio* gpio) {
        hal_ = gpio;
    }

    void registerChannel(int ch, int pin, int mode) {
        if (ch < 0 || ch >= MAX_CHANNELS) {
            DBG_PRINTF("[GPIO] registerChannel: invalid ch=%d (max=%d)\n",
                       ch, MAX_CHANNELS - 1);
            return;
        }
        if (!hal_) {
            DBG_PRINTLN("[GPIO] registerChannel: HAL not set!");
            return;
        }

        DBG_PRINTF("[GPIO] registerChannel: ch=%d pin=%d mode=%d\n",
                   ch, pin, mode);

        // Convert int mode to HAL PinMode
        hal::PinMode halMode;
        switch (mode) {
            case 0x01: halMode = hal::PinMode::Input; break;       // INPUT
            case 0x02: halMode = hal::PinMode::Output; break;      // OUTPUT
            case 0x05: halMode = hal::PinMode::InputPullup; break; // INPUT_PULLUP
            default:   halMode = hal::PinMode::Output; break;
        }

        hal_->pinMode(static_cast<uint8_t>(pin), halMode);
        pinForChannel_[ch] = static_cast<int8_t>(pin);
    }

    bool hasChannel(int ch) const {
        if (ch < 0 || ch >= MAX_CHANNELS) {
            return false;
        }
        return pinForChannel_[ch] != -1;
    }

    void write(int ch, int value) {
        if (!hasChannel(ch)) {
            DBG_PRINTF("[GPIO] write: Unknown channel %d\n", ch);
            return;
        }
        if (!hal_) return;

        uint8_t pin = static_cast<uint8_t>(pinForChannel_[ch]);
        hal_->digitalWrite(pin, value ? 1 : 0);
    }

    int read(int ch) const {
        if (!hasChannel(ch)) {
            DBG_PRINTF("[GPIO] read: Unknown channel %d\n", ch);
            return -1;
        }
        if (!hal_) return -1;

        uint8_t pin = static_cast<uint8_t>(pinForChannel_[ch]);
        return hal_->digitalRead(pin);
    }

    void toggle(int ch) {
        if (!hasChannel(ch)) {
            DBG_PRINTF("[GPIO] toggle: Unknown channel %d\n", ch);
            return;
        }
        if (!hal_) return;

        uint8_t pin = static_cast<uint8_t>(pinForChannel_[ch]);
        hal_->toggle(pin);
    }

    void configureLimitSwitch(uint8_t pin) {
        if (!hal_) return;
        hal_->pinMode(pin, hal::PinMode::InputPullup);
    }

private:
    hal::IGpio* hal_ = nullptr;
    int8_t pinForChannel_[MAX_CHANNELS];
};
