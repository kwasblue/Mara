#pragma once

#include "../IClock.h"
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

namespace hal {

/// ESP32 implementation of IClock using Arduino/FreeRTOS
class Esp32Clock : public IClock {
public:
    uint32_t millis() const override {
        return ::millis();
    }

    uint32_t micros() const override {
        return ::micros();
    }

    void delayMs(uint32_t ms) override {
        // Use FreeRTOS delay to yield to scheduler
        vTaskDelay(pdMS_TO_TICKS(ms));
    }

    void delayUs(uint32_t us) override {
        if (us >= 1000) {
            // For longer delays, use FreeRTOS (yields)
            vTaskDelay(pdMS_TO_TICKS(us / 1000));
            us = us % 1000;
        }
        if (us > 0) {
            // Short delays use busy-wait
            ::delayMicroseconds(us);
        }
    }

    void busyWaitUs(uint32_t us) override {
        ::delayMicroseconds(us);
    }

    uint32_t getTicks() const override {
        return xTaskGetTickCount();
    }

    uint32_t msToTicks(uint32_t ms) const override {
        return pdMS_TO_TICKS(ms);
    }

    uint32_t ticksToMs(uint32_t ticks) const override {
        return ticks * portTICK_PERIOD_MS;
    }
};

} // namespace hal
