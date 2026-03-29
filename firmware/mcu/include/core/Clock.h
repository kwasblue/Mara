// include/core/Clock.h
// Time abstraction for testability and deterministic replay

#pragma once

#include <cstdint>

namespace mara {

/**
 * Clock interface for time abstraction.
 *
 * Allows injecting mock clocks for testing and deterministic replay.
 * Production code uses SystemClock which wraps Arduino millis()/micros().
 */
class IClock {
public:
    virtual ~IClock() = default;

    /// Get current time in milliseconds
    virtual uint32_t millis() const = 0;

    /// Get current time in microseconds
    virtual uint32_t micros() const = 0;

    /// Delay for specified milliseconds (blocking)
    virtual void delay(uint32_t ms) = 0;

    /// Delay for specified microseconds (blocking)
    virtual void delayMicroseconds(uint32_t us) = 0;
};

/**
 * System clock implementation using Arduino functions.
 * This is the default clock for production use.
 */
class SystemClock : public IClock {
public:
    uint32_t millis() const override;
    uint32_t micros() const override;
    void delay(uint32_t ms) override;
    void delayMicroseconds(uint32_t us) override;
};

/**
 * Mock clock for testing.
 * Allows manual control of time for deterministic tests.
 */
class MockClock : public IClock {
public:
    uint32_t millis() const override { return millis_; }
    uint32_t micros() const override { return micros_; }

    /// delay() in mock clock advances time (non-blocking simulation)
    void delay(uint32_t ms) override { advanceMillis(ms); }

    /// delayMicroseconds() in mock clock advances time
    void delayMicroseconds(uint32_t us) override { advanceMicros(us); }

    /// Set current millisecond time
    void setMillis(uint32_t ms) { millis_ = ms; micros_ = ms * 1000; }

    /// Set current microsecond time
    void setMicros(uint32_t us) { micros_ = us; millis_ = us / 1000; }

    /// Advance time by milliseconds
    void advanceMillis(uint32_t delta) {
        millis_ += delta;
        micros_ += delta * 1000;
    }

    /// Advance time by microseconds
    void advanceMicros(uint32_t delta) {
        micros_ += delta;
        millis_ = micros_ / 1000;
    }

private:
    uint32_t millis_ = 0;
    uint32_t micros_ = 0;
};

/// Get the global system clock instance (for cases where DI isn't practical)
SystemClock& getSystemClock();

} // namespace mara
