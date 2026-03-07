#include "hal/esp32/Esp32Watchdog.h"
#include <esp_task_wdt.h>

namespace hal {

bool Esp32Watchdog::begin(uint32_t timeoutSeconds, bool panicOnTimeout) {
    esp_err_t err = esp_task_wdt_init(timeoutSeconds, panicOnTimeout);
    if (err == ESP_OK || err == ESP_ERR_INVALID_STATE) {
        // ESP_ERR_INVALID_STATE means already initialized, which is fine
        enabled_ = true;
        return true;
    }
    return false;
}

bool Esp32Watchdog::addCurrentTask() {
    esp_err_t err = esp_task_wdt_add(NULL);
    return (err == ESP_OK || err == ESP_ERR_INVALID_ARG); // INVALID_ARG = already added
}

bool Esp32Watchdog::removeCurrentTask() {
    esp_err_t err = esp_task_wdt_delete(NULL);
    return (err == ESP_OK);
}

void Esp32Watchdog::reset() {
    esp_task_wdt_reset();
}

} // namespace hal
