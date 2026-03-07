// include/core/Debug.h
#pragma once

// Toggle this per env or per build.
// Default: OFF (0) so logs compile out unless explicitly enabled.
#ifndef ENABLE_DEBUG_LOGS
#define ENABLE_DEBUG_LOGS 0
#endif

#if ENABLE_DEBUG_LOGS

  // For firmware builds, Serial is available via Arduino.h
  // (If ENABLE_DEBUG_LOGS is never enabled in native tests, this won't matter.)
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

#endif
