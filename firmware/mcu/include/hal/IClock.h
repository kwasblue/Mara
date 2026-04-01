#pragma once

#include <cstdint>

namespace hal {

/// Abstract clock/timing interface for platform portability
///
/// Provides millisecond and microsecond timing without platform-specific calls.
/// All methods are non-blocking unless otherwise specified.
///
/// Thread Safety: All methods are safe to call from any context (ISR-safe where noted).
///
/// Contract:
/// - millis()/micros() must be monotonic (may wrap at 32-bit limit)
/// - delayMs()/delayUs() may yield to scheduler on RTOS platforms
/// - busyWaitUs() never yields (use sparingly, ISR-safe)
class IClock {
public:
    virtual ~IClock() = default;

    /// Get milliseconds since boot (wraps at ~49 days)
    /// @note ISR-safe
    virtual uint32_t millis() const = 0;

    /// Get microseconds since boot (wraps at ~71 minutes)
    /// @note ISR-safe
    virtual uint32_t micros() const = 0;

    /// Delay for specified milliseconds
    /// @note May yield to scheduler on RTOS platforms
    /// @note NOT ISR-safe
    virtual void delayMs(uint32_t ms) = 0;

    /// Delay for specified microseconds
    /// @note May yield to scheduler for longer delays
    /// @note NOT ISR-safe for delays > 10µs
    virtual void delayUs(uint32_t us) = 0;

    /// Busy-wait for specified microseconds (no yield)
    /// @note ISR-safe, but blocks CPU — use sparingly
    /// @note For delays < 10µs where precision matters
    virtual void busyWaitUs(uint32_t us) = 0;

    /// Get system tick count (platform-specific resolution)
    /// @note Useful for RTOS-aware timing
    virtual uint32_t getTicks() const = 0;

    /// Convert milliseconds to platform ticks
    virtual uint32_t msToTicks(uint32_t ms) const = 0;

    /// Convert platform ticks to milliseconds
    virtual uint32_t ticksToMs(uint32_t ticks) const = 0;
};

} // namespace hal
