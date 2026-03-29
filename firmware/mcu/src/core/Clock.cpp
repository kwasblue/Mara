// src/core/Clock.cpp

#include "core/Clock.h"
#include "config/PlatformConfig.h"

#if PLATFORM_HAS_ARDUINO
#include <Arduino.h>
#else
// Native build stubs
extern "C" {
    extern uint32_t __test_millis;
    extern uint32_t __test_micros;
}
// For native builds, provide a simple busy-wait delay stub
#include <thread>
#include <chrono>
#endif

namespace mara {

uint32_t SystemClock::millis() const {
#if PLATFORM_HAS_ARDUINO
    return ::millis();
#else
    return __test_millis;
#endif
}

uint32_t SystemClock::micros() const {
#if PLATFORM_HAS_ARDUINO
    return ::micros();
#else
    return __test_micros;
#endif
}

void SystemClock::delay(uint32_t ms) {
#if PLATFORM_HAS_ARDUINO
    ::delay(ms);
#else
    // Native build: use std::this_thread::sleep_for
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
#endif
}

void SystemClock::delayMicroseconds(uint32_t us) {
#if PLATFORM_HAS_ARDUINO
    ::delayMicroseconds(us);
#else
    // Native build: use std::this_thread::sleep_for
    std::this_thread::sleep_for(std::chrono::microseconds(us));
#endif
}

// Global system clock instance
static SystemClock g_systemClock;

SystemClock& getSystemClock() {
    return g_systemClock;
}

} // namespace mara
