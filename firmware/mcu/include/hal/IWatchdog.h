#pragma once

#include <cstdint>

namespace hal {

/// Abstract watchdog timer interface for platform portability
/// Provides system-level watchdog for detecting hangs/crashes
class IWatchdog {
public:
    virtual ~IWatchdog() = default;

    /// Initialize watchdog with timeout in seconds
    /// @param timeoutSeconds Timeout before reset (typically 1-10s)
    /// @param panicOnTimeout If true, trigger reset on timeout
    /// @return true if successful
    virtual bool begin(uint32_t timeoutSeconds, bool panicOnTimeout = true) = 0;

    /// Add current task to watchdog monitoring
    /// @return true if successful
    virtual bool addCurrentTask() = 0;

    /// Remove current task from watchdog monitoring
    /// @return true if successful
    virtual bool removeCurrentTask() = 0;

    /// Reset (feed) the watchdog timer
    /// Must be called periodically to prevent reset
    virtual void reset() = 0;

    /// Check if watchdog is enabled
    virtual bool isEnabled() const = 0;
};

} // namespace hal
