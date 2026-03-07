#pragma once

#include "../ITimer.h"

// Forward declare ESP-IDF timer handle
struct esp_timer;
typedef struct esp_timer* esp_timer_handle_t;

namespace hal {

/// ESP32 timer implementation using esp_timer API
class Esp32Timer : public ITimer {
public:
    Esp32Timer();
    ~Esp32Timer();

    bool startRepeating(uint32_t intervalUs, TimerCallback callback) override;
    bool startOnce(uint32_t delayUs, TimerCallback callback) override;
    void stop() override;
    bool isRunning() const override;
    uint64_t micros() const override;
    uint32_t millis() const override;
    void delayMicros(uint32_t us) override;
    void delayMillis(uint32_t ms) override;

private:
    esp_timer_handle_t timerHandle_ = nullptr;
    bool running_ = false;

    void createTimer(TimerCallback callback);
    void deleteTimer();
};

} // namespace hal
