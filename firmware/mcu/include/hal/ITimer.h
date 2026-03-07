#pragma once

#include <cstdint>

namespace hal {

/// Timer callback type
using TimerCallback = void (*)();

/// Abstract timer interface for platform portability
class ITimer {
public:
    virtual ~ITimer() = default;

    /// Start a repeating timer
    /// @param intervalUs Interval in microseconds
    /// @param callback Function to call on each tick
    /// @return true if successful
    virtual bool startRepeating(uint32_t intervalUs, TimerCallback callback) = 0;

    /// Start a one-shot timer
    /// @param delayUs Delay in microseconds
    /// @param callback Function to call when timer fires
    /// @return true if successful
    virtual bool startOnce(uint32_t delayUs, TimerCallback callback) = 0;

    /// Stop the timer
    virtual void stop() = 0;

    /// Check if timer is running
    virtual bool isRunning() const = 0;

    /// Get current time in microseconds (platform monotonic clock)
    virtual uint64_t micros() const = 0;

    /// Get current time in milliseconds
    virtual uint32_t millis() const = 0;

    /// Delay for specified microseconds (blocking)
    virtual void delayMicros(uint32_t us) = 0;

    /// Delay for specified milliseconds (blocking)
    virtual void delayMillis(uint32_t ms) = 0;
};

} // namespace hal
