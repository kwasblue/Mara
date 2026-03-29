#pragma once

#include <cstdint>

namespace hal {

/// Platform-specific spinlock handle
/// Each platform defines its own struct to hold the spinlock state.
/// ESP32: wraps portMUX_TYPE
/// STM32: wraps PRIMASK state or similar
/// Native: empty stub for testing
struct SpinlockHandle {
    // Platform implementations will define the actual storage
    // Use alignas to ensure proper alignment for any platform
    alignas(8) uint8_t storage[16];
};

/// Abstract critical section interface for platform portability
/// Provides spinlock-based critical sections for real-time safe code.
///
/// Usage:
///   ICriticalSection* critical = hal.critical;
///   SpinlockHandle lock;
///   critical->initSpinlock(lock);
///
///   critical->enterCritical(lock);
///   // ... protected code ...
///   critical->exitCritical(lock);
///
/// Thread Safety:
///   - Uses spinlock (not mutex) for minimal latency
///   - Safe for ISR context via enterCriticalISR/exitCriticalISR
///   - Non-blocking: spins until lock acquired
///   - Prevents preemption within critical section
class ICriticalSection {
public:
    virtual ~ICriticalSection() = default;

    /// Initialize a spinlock handle
    /// @param lock Reference to spinlock to initialize
    virtual void initSpinlock(SpinlockHandle& lock) = 0;

    /// Enter critical section (acquires spinlock)
    /// @param lock Reference to initialized spinlock
    virtual void enterCritical(SpinlockHandle& lock) = 0;

    /// Exit critical section (releases spinlock)
    /// @param lock Reference to spinlock
    virtual void exitCritical(SpinlockHandle& lock) = 0;

    /// Enter critical section from ISR context
    /// @param lock Reference to initialized spinlock
    virtual void enterCriticalISR(SpinlockHandle& lock) = 0;

    /// Exit critical section from ISR context
    /// @param lock Reference to spinlock
    virtual void exitCriticalISR(SpinlockHandle& lock) = 0;
};

} // namespace hal
