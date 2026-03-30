#pragma once

#include <string>
#include <cstdint>
#include <unordered_map>

#include "core/EventBus.h"
#include "core/Event.h"
#include "core/IModule.h"

/**
 * LoggingModule - Centralized logging with per-subsystem level control.
 *
 * Provides two logging paths:
 * 1. Local serial output via DBG_PRINT (compile-time controlled)
 * 2. Remote host logging via JSON (runtime level controlled)
 *
 * Usage in handlers:
 *   MARA_LOG_DEBUG("servo", "Attached id=%d pin=%d", id, pin);
 *   MARA_LOG_INFO("stepper", "Move complete");
 *   MARA_LOG_WARN("motor", "Overcurrent detected");
 *   MARA_LOG_ERROR("gpio", "Invalid pin %d", pin);
 *
 * Per-subsystem levels can be set via CMD_SET_SUBSYSTEM_LOG_LEVEL:
 *   {"subsystem": "servo", "level": "debug"}
 */
class LoggingModule : public IModule {
public:
    enum class LogLevel : uint8_t {
        DEBUG = 0,
        INFO  = 1,
        WARN  = 2,
        ERROR = 3,
        OFF   = 4
    };

    explicit LoggingModule(EventBus& bus)
        : bus_(bus)
        , globalLevel_(LogLevel::INFO)  // default verbosity
    {}

    // IModule interface
    void setup() override;
    void loop(uint32_t now_ms) override;
    void handleEvent(const Event& evt) override;

    static void onEventStatic(const Event& evt);

    // Access to singleton instance
    static LoggingModule* instance() { return s_instance; }

    // ---------------------------------------------------------------------------
    // Global log level (applies to all subsystems without specific level)
    // ---------------------------------------------------------------------------
    void setLogLevel(const char* levelStr);
    LogLevel currentLevel() const { return globalLevel_; }

    // ---------------------------------------------------------------------------
    // Per-subsystem log level control
    // ---------------------------------------------------------------------------

    /**
     * Set log level for a specific subsystem.
     * @param subsystem Subsystem name (e.g., "servo", "stepper", "motor")
     * @param levelStr Level string ("debug", "info", "warn", "error", "off")
     */
    void setSubsystemLevel(const char* subsystem, const char* levelStr);

    /**
     * Get effective log level for a subsystem.
     * Returns subsystem-specific level if set, otherwise global level.
     */
    LogLevel getEffectiveLevel(const char* subsystem) const;

    /**
     * Clear all per-subsystem levels (revert to global level).
     */
    void clearSubsystemLevels();

    /**
     * List current subsystem levels (for diagnostics).
     * Returns JSON object: {"servo": "debug", "stepper": "info", ...}
     */
    std::string getSubsystemLevelsJson() const;

    // ---------------------------------------------------------------------------
    // Static logging API (for use from handlers via macros)
    // ---------------------------------------------------------------------------

    /**
     * Log a message if it passes level filtering.
     * This is the main entry point for subsystem logging.
     *
     * @param subsystem Subsystem name (e.g., "servo", "motor")
     * @param level Log level for this message
     * @param fmt Printf-style format string
     * @param ... Format arguments
     */
    static void log(const char* subsystem, LogLevel level, const char* fmt, ...);

    // Convenience static methods
    static void logDebug(const char* subsystem, const char* fmt, ...);
    static void logInfo(const char* subsystem, const char* fmt, ...);
    static void logWarn(const char* subsystem, const char* fmt, ...);
    static void logError(const char* subsystem, const char* fmt, ...);

    // Check if a log at given level would be emitted (for expensive formatting)
    static bool wouldLog(const char* subsystem, LogLevel level);

    const char* name() const override { return "LoggingModule"; }

    // Convert level enum to string
    static const char* levelToString(LogLevel level);

private:
    LogLevel parseLevel(const char* s) const;

    // Forward logs to Python host as JSON
    void sendLog(const char* level,
                 const char* tag,
                 const char* msg,
                 uint32_t ts_ms);

    void sendLogJson(const char* level,
                     const char* tag,
                     const std::string& json,
                     uint32_t ts_ms);

    // Internal log implementation (called by static methods)
    void doLog(const char* subsystem, LogLevel level, const char* msg);

    EventBus&      bus_;
    static LoggingModule* s_instance;

    LogLevel       globalLevel_;
    std::unordered_map<std::string, LogLevel> subsystemLevels_;
};

// ---------------------------------------------------------------------------
// Convenience macros for logging from handlers
// ---------------------------------------------------------------------------

#define MARA_LOG_DEBUG(subsystem, fmt, ...) \
    LoggingModule::logDebug(subsystem, fmt, ##__VA_ARGS__)

#define MARA_LOG_INFO(subsystem, fmt, ...) \
    LoggingModule::logInfo(subsystem, fmt, ##__VA_ARGS__)

#define MARA_LOG_WARN(subsystem, fmt, ...) \
    LoggingModule::logWarn(subsystem, fmt, ##__VA_ARGS__)

#define MARA_LOG_ERROR(subsystem, fmt, ...) \
    LoggingModule::logError(subsystem, fmt, ##__VA_ARGS__)

// Check before expensive formatting
#define MARA_WOULD_LOG(subsystem, level) \
    LoggingModule::wouldLog(subsystem, LoggingModule::LogLevel::level)
