// include/hal/ILogger.h
// Abstract logger interface for platform portability.
// Replaces direct Serial.print() calls with injectable logging.
#pragma once

#include <cstdint>
#include <cstdarg>
#include <cstdio>

namespace hal {

/// Log levels in order of severity
enum class LogLevel : uint8_t {
    TRACE = 0,  // Very detailed debugging
    DEBUG = 1,  // Debugging information
    INFO  = 2,  // Normal operational messages
    WARN  = 3,  // Warning conditions
    ERROR = 4,  // Error conditions
    NONE  = 5   // Disable all logging
};

/// Abstract logger interface
/// Implementations wrap platform-specific output (Serial, stdout, etc.)
///
/// Usage:
///   ILogger* logger = hal.logger;
///   logger->info("System started");
///   logger->printf(LogLevel::DEBUG, "Value: %d", 42);
///
/// Log levels can be filtered at runtime via setLevel().
class ILogger {
public:
    virtual ~ILogger() = default;

    // =========================================================================
    // Configuration
    // =========================================================================

    /// Set minimum log level (messages below this are filtered)
    virtual void setLevel(LogLevel level) = 0;

    /// Get current log level
    virtual LogLevel getLevel() const = 0;

    // =========================================================================
    // Basic output (no level filtering)
    // =========================================================================

    /// Print string without newline
    virtual void print(const char* msg) = 0;

    /// Print string with newline
    virtual void println(const char* msg) = 0;

    /// Print empty newline
    virtual void println() = 0;

    /// Printf-style output
    virtual void printf(const char* fmt, ...) = 0;

    // =========================================================================
    // Level-aware logging
    // =========================================================================

    /// Log with explicit level and printf formatting
    virtual void log(LogLevel level, const char* fmt, ...) = 0;

    /// Convenience methods for each level
    void trace(const char* fmt, ...) {
        if (getLevel() > LogLevel::TRACE) return;
        va_list args;
        va_start(args, fmt);
        vlog(LogLevel::TRACE, fmt, args);
        va_end(args);
    }

    void debug(const char* fmt, ...) {
        if (getLevel() > LogLevel::DEBUG) return;
        va_list args;
        va_start(args, fmt);
        vlog(LogLevel::DEBUG, fmt, args);
        va_end(args);
    }

    void info(const char* fmt, ...) {
        if (getLevel() > LogLevel::INFO) return;
        va_list args;
        va_start(args, fmt);
        vlog(LogLevel::INFO, fmt, args);
        va_end(args);
    }

    void warn(const char* fmt, ...) {
        if (getLevel() > LogLevel::WARN) return;
        va_list args;
        va_start(args, fmt);
        vlog(LogLevel::WARN, fmt, args);
        va_end(args);
    }

    void error(const char* fmt, ...) {
        if (getLevel() > LogLevel::ERROR) return;
        va_list args;
        va_start(args, fmt);
        vlog(LogLevel::ERROR, fmt, args);
        va_end(args);
    }

protected:
    /// Internal variadic log - implementations must override this
    virtual void vlog(LogLevel level, const char* fmt, va_list args) = 0;
};

/// Convert log level to string prefix
inline const char* logLevelPrefix(LogLevel level) {
    switch (level) {
        case LogLevel::TRACE: return "[TRACE] ";
        case LogLevel::DEBUG: return "[DEBUG] ";
        case LogLevel::INFO:  return "[INFO]  ";
        case LogLevel::WARN:  return "[WARN]  ";
        case LogLevel::ERROR: return "[ERROR] ";
        default:              return "";
    }
}

} // namespace hal
