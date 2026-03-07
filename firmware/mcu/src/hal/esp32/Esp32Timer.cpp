#include "hal/esp32/Esp32Timer.h"
#include <Arduino.h>
#include <esp_timer.h>

namespace hal {

// Static callback wrapper for esp_timer
static TimerCallback s_currentCallback = nullptr;

static void IRAM_ATTR timerCallbackWrapper(void* arg) {
    if (s_currentCallback) {
        s_currentCallback();
    }
}

Esp32Timer::Esp32Timer() {}

Esp32Timer::~Esp32Timer() {
    stop();
    deleteTimer();
}

void Esp32Timer::createTimer(TimerCallback callback) {
    if (timerHandle_ != nullptr) {
        deleteTimer();
    }

    s_currentCallback = callback;

    esp_timer_create_args_t timerArgs = {};
    timerArgs.callback = timerCallbackWrapper;
    timerArgs.arg = nullptr;
    timerArgs.dispatch_method = ESP_TIMER_TASK;
    timerArgs.name = "hal_timer";

    esp_timer_create(&timerArgs, &timerHandle_);
}

void Esp32Timer::deleteTimer() {
    if (timerHandle_ != nullptr) {
        esp_timer_delete(timerHandle_);
        timerHandle_ = nullptr;
    }
    s_currentCallback = nullptr;
}

bool Esp32Timer::startRepeating(uint32_t intervalUs, TimerCallback callback) {
    stop();
    createTimer(callback);

    if (timerHandle_ == nullptr) return false;

    esp_err_t err = esp_timer_start_periodic(timerHandle_, intervalUs);
    if (err == ESP_OK) {
        running_ = true;
        return true;
    }
    return false;
}

bool Esp32Timer::startOnce(uint32_t delayUs, TimerCallback callback) {
    stop();
    createTimer(callback);

    if (timerHandle_ == nullptr) return false;

    esp_err_t err = esp_timer_start_once(timerHandle_, delayUs);
    if (err == ESP_OK) {
        running_ = true;
        return true;
    }
    return false;
}

void Esp32Timer::stop() {
    if (timerHandle_ != nullptr && running_) {
        esp_timer_stop(timerHandle_);
        running_ = false;
    }
}

bool Esp32Timer::isRunning() const {
    return running_;
}

uint64_t Esp32Timer::micros() const {
    return esp_timer_get_time();
}

uint32_t Esp32Timer::millis() const {
    return (uint32_t)(esp_timer_get_time() / 1000);
}

void Esp32Timer::delayMicros(uint32_t us) {
    delayMicroseconds(us);
}

void Esp32Timer::delayMillis(uint32_t ms) {
    delay(ms);
}

} // namespace hal
