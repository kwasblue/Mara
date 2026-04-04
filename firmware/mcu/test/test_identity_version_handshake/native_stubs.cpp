// test/test_identity_version_handshake/native_stubs.cpp
// Minimal stubs required for IdentityModule native tests

#ifdef PIO_UNIT_TESTING

#include <cstdint>

// -------------------- Time stubs for native tests --------------------
extern "C" {
    uint32_t __test_millis = 0;
    uint32_t __test_micros = 0;
}

// -------------------- Clock stubs --------------------
#include "core/Clock.h"

namespace mara {

uint32_t SystemClock::millis() const { return __test_millis; }
uint32_t SystemClock::micros() const { return __test_micros; }
void SystemClock::delay(uint32_t ms) { __test_millis += ms; __test_micros += ms * 1000; }
void SystemClock::delayMicroseconds(uint32_t us) { __test_micros += us; __test_millis = __test_micros / 1000; }

static SystemClock g_systemClock;

SystemClock& getSystemClock() { return g_systemClock; }

} // namespace mara

#endif // PIO_UNIT_TESTING
