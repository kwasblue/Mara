#pragma once

#include <Arduino.h>
#include "esp_task_wdt.h"
#include "config/DefaultSettings.h"

namespace Watchdog {

// Initialize hardware watchdog
inline bool init(uint32_t timeoutSeconds = WATCHDOG_TIMEOUT_S) {
    // Use the simpler API for ESP-IDF 4.x compatibility
    esp_err_t err = esp_task_wdt_init(timeoutSeconds, true);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return false;
    }

    err = esp_task_wdt_add(NULL);
    if (err != ESP_OK && err != ESP_ERR_INVALID_ARG) {
        return false;
    }

    return true;
}

// Reset watchdog timer (call periodically)
inline void feed() {
    esp_task_wdt_reset();
}

// Remove current task from watchdog
inline void deinit() {
    esp_task_wdt_delete(NULL);
}

} // namespace Watchdog
