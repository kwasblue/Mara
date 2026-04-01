// test/test_benchmark_module/native_stubs.cpp
// Stubs for native testing of benchmark components

#include "core/Clock.h"

// ============================================================================
// Time stubs - auto-increment to simulate time passing
// ============================================================================
extern "C" {
    uint32_t __test_millis = 0;
    uint32_t __test_micros = 0;
}

namespace mara {

uint32_t SystemClock::millis() const {
    // Auto-increment by 1ms each call to simulate time passing
    __test_millis += 1;
    return __test_millis;
}

uint32_t SystemClock::micros() const {
    // Auto-increment by 100us each call to simulate benchmark timing
    __test_micros += 100;
    __test_millis = __test_micros / 1000;
    return __test_micros;
}
void SystemClock::delay(uint32_t ms) { __test_millis += ms; __test_micros += ms * 1000; }
void SystemClock::delayMicroseconds(uint32_t us) { __test_micros += us; __test_millis = __test_micros / 1000; }

static SystemClock g_systemClock;

SystemClock& getSystemClock() { return g_systemClock; }

} // namespace mara
