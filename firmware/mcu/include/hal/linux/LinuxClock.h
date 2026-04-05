// include/hal/linux/LinuxClock.h
// Linux clock implementation using clock_gettime(CLOCK_MONOTONIC)
#pragma once

// Enable POSIX features for clock_nanosleep
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include "../IClock.h"
#include <cstdint>
#include <ctime>
#include <unistd.h>

namespace hal {

/// Linux implementation of IClock using clock_gettime
///
/// Provides high-resolution timing via CLOCK_MONOTONIC.
/// Supports both yielding delays (clock_nanosleep) and busy-waits.
class LinuxClock : public IClock {
public:
    LinuxClock() {
        // Record boot time
        clock_gettime(CLOCK_MONOTONIC, &bootTime_);
    }

    uint32_t millis() const override {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        uint64_t elapsed_ns = (now.tv_sec - bootTime_.tv_sec) * 1000000000ULL +
                              (now.tv_nsec - bootTime_.tv_nsec);
        return static_cast<uint32_t>(elapsed_ns / 1000000ULL);
    }

    uint32_t micros() const override {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        uint64_t elapsed_ns = (now.tv_sec - bootTime_.tv_sec) * 1000000000ULL +
                              (now.tv_nsec - bootTime_.tv_nsec);
        return static_cast<uint32_t>(elapsed_ns / 1000ULL);
    }

    void delayMs(uint32_t ms) override {
        struct timespec ts;
        ts.tv_sec = ms / 1000;
        ts.tv_nsec = (ms % 1000) * 1000000L;
        clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, nullptr);
    }

    void delayUs(uint32_t us) override {
        if (us >= 1000) {
            // Use nanosleep for longer delays (yields CPU)
            struct timespec ts;
            ts.tv_sec = us / 1000000;
            ts.tv_nsec = (us % 1000000) * 1000L;
            clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, nullptr);
        } else {
            // Short delay: busy wait for precision
            busyWaitUs(us);
        }
    }

    void busyWaitUs(uint32_t us) override {
        struct timespec start, now;
        clock_gettime(CLOCK_MONOTONIC, &start);
        uint64_t target_ns = static_cast<uint64_t>(us) * 1000ULL;

        do {
            clock_gettime(CLOCK_MONOTONIC, &now);
            uint64_t elapsed_ns = (now.tv_sec - start.tv_sec) * 1000000000ULL +
                                  (now.tv_nsec - start.tv_nsec);
            if (elapsed_ns >= target_ns) break;
        } while (true);
    }

    uint32_t getTicks() const override {
        // Simulate 1ms tick resolution (same as native)
        return millis();
    }

    uint32_t msToTicks(uint32_t ms) const override {
        return ms;  // 1:1 conversion
    }

    uint32_t ticksToMs(uint32_t ticks) const override {
        return ticks;  // 1:1 conversion
    }

private:
    struct timespec bootTime_;
};

} // namespace hal
