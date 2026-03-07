// include/core/CriticalSection.h
// RAII guard for critical sections on ESP32 (FreeRTOS spinlock)
//
// Usage:
//   {
//       mara::CriticalSection lock(lock_);
//       // ... protected code ...
//   }  // Automatically exits critical section
//
// Thread Safety:
//   - Uses spinlock (not mutex) for minimal latency
//   - Safe for ISR context on ESP32
//   - Non-blocking: spins until lock acquired
//   - Prevents preemption within critical section
//
// Guidelines:
//   - Keep critical sections SHORT (< 10μs ideal)
//   - No blocking calls inside (no delay, no I/O waits)
//   - No heap allocation inside
//   - Prefer snapshot pattern for bulk reads

#pragma once

#include <cstdint>

#ifdef ESP32
#include <freertos/FreeRTOS.h>
#include <freertos/portmacro.h>
#endif

namespace mara {

// =============================================================================
// Spinlock Type (platform-specific)
// =============================================================================

#ifdef ESP32
using SpinlockType = portMUX_TYPE;
#define MCU_SPINLOCK_INIT portMUX_INITIALIZER_UNLOCKED
#else
// Stub for native testing - no actual locking
struct SpinlockStub {};
using SpinlockType = SpinlockStub;
#define MCU_SPINLOCK_INIT ::mara::SpinlockStub{}
#endif

// =============================================================================
// CriticalSection RAII Guard
// =============================================================================

/// RAII guard for spinlock-based critical sections.
/// Automatically enters on construction, exits on destruction.
class CriticalSection {
public:
    /// Enter critical section (acquires spinlock)
    explicit CriticalSection(SpinlockType& lock) : lock_(lock) {
        enter();
    }

    /// Exit critical section (releases spinlock)
    ~CriticalSection() {
        exit();
    }

    // Non-copyable, non-movable
    CriticalSection(const CriticalSection&) = delete;
    CriticalSection& operator=(const CriticalSection&) = delete;
    CriticalSection(CriticalSection&&) = delete;
    CriticalSection& operator=(CriticalSection&&) = delete;

private:
    SpinlockType& lock_;

    void enter() {
#ifdef ESP32
        portENTER_CRITICAL(&lock_);
#else
        (void)lock_;  // No-op for native tests
#endif
    }

    void exit() {
#ifdef ESP32
        portEXIT_CRITICAL(&lock_);
#else
        (void)lock_;  // No-op for native tests
#endif
    }
};

// =============================================================================
// Spinlock Initialization Helper
// =============================================================================

/// Initialize a spinlock (call once at construction)
inline void initSpinlock([[maybe_unused]] SpinlockType& lock) {
#ifdef ESP32
    spinlock_initialize(&lock);
#endif
}

// =============================================================================
// ISR-Safe Critical Section (for interrupt handlers)
// =============================================================================

#ifdef ESP32
/// RAII guard for ISR-safe critical sections.
/// Use this when the critical section may be entered from an ISR.
class CriticalSectionISR {
public:
    explicit CriticalSectionISR(SpinlockType& lock) : lock_(lock) {
        portENTER_CRITICAL_ISR(&lock_);
    }

    ~CriticalSectionISR() {
        portEXIT_CRITICAL_ISR(&lock_);
    }

    CriticalSectionISR(const CriticalSectionISR&) = delete;
    CriticalSectionISR& operator=(const CriticalSectionISR&) = delete;

private:
    SpinlockType& lock_;
};
#else
// Native stub - same as regular CriticalSection
using CriticalSectionISR = CriticalSection;
#endif

} // namespace mara
