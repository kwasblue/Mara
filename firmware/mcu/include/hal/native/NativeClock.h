#pragma once

#include "../IClock.h"
#include <chrono>
#include <thread>

namespace hal {

/// Native (desktop) implementation of IClock using std::chrono
///
/// For unit testing and simulation without hardware.
/// Tick resolution is 1ms (simulated).
class NativeClock : public IClock {
public:
    NativeClock() : bootTime_(std::chrono::steady_clock::now()) {}

    uint32_t millis() const override {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - bootTime_);
        return static_cast<uint32_t>(elapsed.count());
    }

    uint32_t micros() const override {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(now - bootTime_);
        return static_cast<uint32_t>(elapsed.count());
    }

    void delayMs(uint32_t ms) override {
        std::this_thread::sleep_for(std::chrono::milliseconds(ms));
    }

    void delayUs(uint32_t us) override {
        std::this_thread::sleep_for(std::chrono::microseconds(us));
    }

    void busyWaitUs(uint32_t us) override {
        // Busy wait using high-resolution clock
        auto start = std::chrono::steady_clock::now();
        auto target = start + std::chrono::microseconds(us);
        while (std::chrono::steady_clock::now() < target) {
            // Spin
        }
    }

    uint32_t getTicks() const override {
        // Simulate 1ms tick resolution
        return millis();
    }

    uint32_t msToTicks(uint32_t ms) const override {
        return ms;  // 1:1 for native
    }

    uint32_t ticksToMs(uint32_t ticks) const override {
        return ticks;  // 1:1 for native
    }

private:
    std::chrono::steady_clock::time_point bootTime_;
};

} // namespace hal
