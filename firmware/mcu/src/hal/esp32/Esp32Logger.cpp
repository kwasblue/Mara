// src/hal/esp32/Esp32Logger.cpp
// ESP32 logger implementation - most methods are inline in header
// This file is for any non-inline implementations if needed

#include "config/PlatformConfig.h"

#if PLATFORM_ESP32

#include "hal/esp32/Esp32Logger.h"

// All methods are inline in header for now
// This file exists for future expansion and to satisfy build system

namespace hal {

// Static instance for global access if needed
static Esp32Logger g_defaultLogger;

Esp32Logger& getDefaultLogger() {
    return g_defaultLogger;
}

} // namespace hal

#endif // PLATFORM_ESP32
