// include/hal/stubs/StubTimer.h
// Stub timer implementation for native/test builds
#pragma once

#include "../ITimer.h"
#include <chrono>

namespace hal {

class StubTimer : public ITimer {
public:
    bool startRepeating(uint32_t intervalUs, TimerCallback callback) override {
        (void)intervalUs; (void)callback;
        running_ = true;
        return true;
    }

    bool startOnce(uint32_t delayUs, TimerCallback callback) override {
        (void)delayUs; (void)callback;
        running_ = true;
        return true;
    }

    void stop() override { running_ = false; }
    bool isRunning() const override { return running_; }

    uint64_t micros() const override {
        auto now = std::chrono::steady_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch());
        return static_cast<uint64_t>(us.count());
    }

    uint32_t millis() const override {
        return static_cast<uint32_t>(micros() / 1000);
    }

    void delayMicros(uint32_t us) override { (void)us; }
    void delayMillis(uint32_t ms) override { (void)ms; }

private:
    bool running_ = false;
};

} // namespace hal
