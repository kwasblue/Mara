// src/core/Clock.cpp

#include "core/Clock.h"

#ifdef ARDUINO
#include <Arduino.h>
#else
// Native build stubs
extern "C" {
    extern uint32_t __test_millis;
    extern uint32_t __test_micros;
}
#endif

namespace mara {

uint32_t SystemClock::millis() const {
#ifdef ARDUINO
    return ::millis();
#else
    return __test_millis;
#endif
}

uint32_t SystemClock::micros() const {
#ifdef ARDUINO
    return ::micros();
#else
    return __test_micros;
#endif
}

// Global system clock instance
static SystemClock g_systemClock;

SystemClock& getSystemClock() {
    return g_systemClock;
}

} // namespace mara
