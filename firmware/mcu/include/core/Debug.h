// include/core/Debug.h
// Debug logging macros.
// When ENABLE_DEBUG_LOGS is set, these use the global debug logger.
// The logger can be set via setDebugLogger() for HAL abstraction.
#pragma once

#include "config/PlatformConfig.h"
#include "config/FeatureFlags.h"

// Forward declare the logger accessor (always available for wiring)
namespace hal { class ILogger; }
namespace mara {
    hal::ILogger* getDebugLogger();
    void setDebugLogger(hal::ILogger* logger);
}

// Toggle this per env or per build.
// Default: OFF (0) so logs compile out unless explicitly enabled.
#ifndef ENABLE_DEBUG_LOGS
#define ENABLE_DEBUG_LOGS 0
#endif

#if ENABLE_DEBUG_LOGS

  // Use HAL logger if available and configured
  #if HAS_HAL_LOGGER
    #ifndef DBG_PRINT
      #define DBG_PRINT(x)           do { if (auto* _l = mara::getDebugLogger()) _l->print(x); } while (0)
    #endif

    #ifndef DBG_PRINTLN
      #define DBG_PRINTLN(x)         do { if (auto* _l = mara::getDebugLogger()) _l->println(x); } while (0)
    #endif

    #ifndef DBG_PRINTF
      #define DBG_PRINTF(fmt, ...)   do { if (auto* _l = mara::getDebugLogger()) _l->printf(fmt, ##__VA_ARGS__); } while (0)
    #endif

  #else
    // Fallback to direct Serial (for gradual migration)
    #if PLATFORM_HAS_ARDUINO
      #include <Arduino.h>

      #ifndef DBG_PRINT
        #define DBG_PRINT(x)           Serial.print(x)
      #endif

      #ifndef DBG_PRINTLN
        #define DBG_PRINTLN(x)         Serial.println(x)
      #endif

      #ifndef DBG_PRINTF
        #define DBG_PRINTF(fmt, ...)   Serial.printf(fmt, ##__VA_ARGS__)
      #endif
    #else
      // Native fallback to stdio
      #include <cstdio>

      #ifndef DBG_PRINT
        #define DBG_PRINT(x)           std::fputs(x, stdout)
      #endif

      #ifndef DBG_PRINTLN
        #define DBG_PRINTLN(x)         std::puts(x)
      #endif

      #ifndef DBG_PRINTF
        #define DBG_PRINTF(fmt, ...)   std::printf(fmt, ##__VA_ARGS__)
      #endif
    #endif
  #endif // HAS_HAL_LOGGER

#else

  // compile-time no-ops so strings/calls get stripped
  #ifndef DBG_PRINT
    #define DBG_PRINT(x)           do {} while (0)
  #endif

  #ifndef DBG_PRINTLN
    #define DBG_PRINTLN(x)         do {} while (0)
  #endif

  #ifndef DBG_PRINTF
    #define DBG_PRINTF(fmt, ...)   do {} while (0)
  #endif

#endif // ENABLE_DEBUG_LOGS
