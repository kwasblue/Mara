#pragma once
#include <cstdint>

// ---- Time stubs for native tests ----
// These are defined as extern "C" so Clock.cpp can access them
extern "C" {
    extern uint32_t __test_millis;
    extern uint32_t __test_micros;
}

inline uint32_t millis() { return __test_millis; }
inline uint32_t micros() { return __test_micros; }
inline void test_set_millis(uint32_t v) { __test_millis = v; __test_micros = v * 1000; }
inline void test_set_micros(uint32_t v) { __test_micros = v; __test_millis = v / 1000; }
inline void test_advance_millis(uint32_t d) { __test_millis += d; __test_micros += d * 1000; }
inline void test_advance_micros(uint32_t d) { __test_micros += d; __test_millis = __test_micros / 1000; }

// ---- debug macro stubs (so DBG_PRINT compiles on native) ----
#ifndef DBG_PRINT
  #define DBG_PRINT(x)      do { (void)(x); } while(0)
#endif
#ifndef DBG_PRINTLN
  #define DBG_PRINTLN(x)    do { (void)(x); } while(0)
#endif
#ifndef DBG_PRINTF
  #define DBG_PRINTF(...)   do { } while(0)
#endif
