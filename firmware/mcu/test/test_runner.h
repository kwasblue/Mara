// test/test_runner.h
// Cross-platform test runner support for Unity tests
// Works on both native (main) and ESP32 (setup/loop)

#pragma once

#include <unity.h>

#ifdef ARDUINO
#include <Arduino.h>
#endif

// Define this macro in your test file before including this header
// to declare your test runner function
//
// Usage:
//   void run_tests() {
//       RUN_TEST(test_foo);
//       RUN_TEST(test_bar);
//   }
//   TEST_RUNNER(run_tests)

#ifdef ARDUINO
// ESP32/Arduino platform - use setup()/loop() pattern
#define TEST_RUNNER(run_func) \
    void setup() { \
        Serial.begin(115200); \
        delay(2000); /* Allow serial to connect */ \
        UNITY_BEGIN(); \
        run_func(); \
        UNITY_END(); \
    } \
    void loop() { \
        /* Tests complete in setup */ \
    }
#else
// Native platform - use main() pattern
#define TEST_RUNNER(run_func) \
    int main(int argc, char** argv) { \
        (void)argc; (void)argv; \
        UNITY_BEGIN(); \
        run_func(); \
        return UNITY_END(); \
    }
#endif
