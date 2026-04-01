// src/core/Clock.cpp
//
// SystemClock now delegates to hal::IClock for platform portability.
// The HAL clock must be set via setHalClock() during initialization.

#include "core/Clock.h"
#include "hal/IClock.h"

namespace mara {

// HAL clock instance (set during HAL initialization)
static hal::IClock* g_halClock = nullptr;

void setHalClock(hal::IClock* clock) {
    g_halClock = clock;
}

hal::IClock* getHalClock() {
    return g_halClock;
}

uint32_t SystemClock::millis() const {
    return g_halClock ? g_halClock->millis() : 0;
}

uint32_t SystemClock::micros() const {
    return g_halClock ? g_halClock->micros() : 0;
}

void SystemClock::delay(uint32_t ms) {
    if (g_halClock) g_halClock->delayMs(ms);
}

void SystemClock::delayMicroseconds(uint32_t us) {
    if (g_halClock) g_halClock->delayUs(us);
}

// Global system clock instance
static SystemClock g_systemClock;

SystemClock& getSystemClock() {
    return g_systemClock;
}

} // namespace mara
