// src/core/DebugLogger.cpp
// Global debug logger accessor implementation

#include "core/Debug.h"
#include "hal/ILogger.h"

namespace mara {

// Global debug logger pointer
static hal::ILogger* g_debugLogger = nullptr;

hal::ILogger* getDebugLogger() {
    return g_debugLogger;
}

void setDebugLogger(hal::ILogger* logger) {
    g_debugLogger = logger;
}

} // namespace mara
