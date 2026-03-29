// include/core/RealTimeContract.h
// Real-time safe contract documentation and enforcement macros
//
// This file documents the real-time safe contract and provides
// macros for runtime verification during development.

#pragma once

#include <cstdint>

/**
 * =============================================================================
 * REAL-TIME SAFE CONTRACT
 * =============================================================================
 *
 * This firmware runs on ESP32 with multiple execution contexts:
 * - ISR context: Interrupt handlers (encoder, timer)
 * - Control task: FreeRTOS task on Core 1 at 100-500 Hz
 * - Main loop: Cooperative scheduling on Core 0 for I/O and telemetry
 *
 * =============================================================================
 * ALLOCATION POLICY
 * =============================================================================
 *
 * SETUP PHASE (allowed allocation):
 *   Location: setup(), ServiceStorage::init*(), REGISTER_* macros
 *   Operations: new, malloc, vector::reserve, string construction
 *   Why: Runs once at boot, before real-time loops start
 *
 * CONTROL LOOP (forbidden allocation):
 *   Location: runControlLoop(), ControlKernel::step(), Observer::update()
 *   Operations: NO new, NO malloc, NO push_back, NO string ops
 *   Why: Must complete in < 1ms with < 100us jitter
 *
 * SAFETY LOOP (forbidden allocation):
 *   Location: runSafetyLoop(), ModeManager::update()
 *   Operations: NO heap allocation
 *   Why: Safety-critical, must always run
 *
 * TELEMETRY LOOP (allowed allocation, bounded):
 *   Location: runTelemetryLoop(), TelemetryModule::loop()
 *   Operations: JsonDocument OK (stack allocated), bounded strings
 *   Why: Lower priority, can tolerate jitter
 *
 * COMMAND HANDLERS (allowed allocation, bounded):
 *   Location: IStringHandler::handle(), CommandRegistry::onJsonCommand()
 *   Operations: JsonDocument OK, bounded strings
 *   Why: Runs in main loop, not time-critical
 *
 * =============================================================================
 * QUEUE DEPTH CONTRACTS
 * =============================================================================
 *
 *   Queue/Buffer              Max Depth    Overflow Policy
 *   ----------------------    ---------    ---------------
 *   IntentBuffer::signals     16           Drop oldest
 *   IntentBuffer::velocity    1            Replace (latest wins)
 *   IntentBuffer::servo       8            Replace per-ID
 *   IntentBuffer::dcMotor     4            Replace per-ID
 *   IntentBuffer::stepper     4            Replace per-ID
 *   EventBus subscribers      16           Static (compile-time)
 *   SignalBus signals         64           Bounded define()
 *   ControlKernel slots       8            Bounded configureSlot()
 *   Observer slots            4            Bounded configure()
 *
 * =============================================================================
 * TIMING BUDGETS
 * =============================================================================
 *
 *   Function                  Max Duration   Called At
 *   ----------------------    ------------   ---------
 *   ControlKernel::step()     500 us         100 Hz (10ms period)
 *   Observer::update()        200 us         200 Hz (5ms period)
 *   SignalBus::set/get()      10 us          Per signal
 *   IntentBuffer::consume*()  5 us           Per intent
 *   runSafetyLoop()           100 us         100 Hz
 *
 * =============================================================================
 * FORBIDDEN OPERATIONS (in hot path)
 * =============================================================================
 *
 * - Heap allocation: new, delete, malloc, free, realloc
 * - Dynamic containers: std::vector::push_back(), resize(), std::string ops
 * - JSON operations: JsonDocument construction, serializeJson
 * - Blocking I/O: Serial.print in hot path, WiFi operations, file I/O
 * - Unbounded loops: while(true) without timeout, recursive calls
 * - Mutex/semaphore waits: xSemaphoreTake with portMAX_DELAY
 *
 * =============================================================================
 * CONTROL-PATH CODE (must be real-time safe)
 * =============================================================================
 *
 * - controlTaskFunc() in SetupControlTask.cpp
 * - ControlKernel::step()
 * - Observer::update()
 * - MotionController::update()
 * - SignalBus::set() / get()
 * - IntentBuffer consume methods
 * - Any code called from the above
 *
 * =============================================================================
 * ALLOWED ALTERNATIVES
 * =============================================================================
 *
 * - Pre-allocated buffers (static arrays, fixed-size containers)
 * - Spinlocks (portENTER_CRITICAL/portEXIT_CRITICAL) for short critical sections
 * - Bounded iteration with known maximum
 * - Fixed-size ring buffers
 *
 * =============================================================================
 */

// Jitter warning threshold in microseconds
#define RT_JITTER_WARN_US 500

namespace mara {

/**
 * Real-time timing statistics for control task monitoring.
 * Track period jitter to detect timing anomalies.
 */
struct RtTimingStats {
    uint32_t min_period_us = UINT32_MAX;  // Minimum observed period
    uint32_t max_period_us = 0;            // Maximum observed period
    uint32_t jitter_violations = 0;        // Count of periods exceeding threshold
    uint32_t target_period_us = 10000;     // Expected period (e.g., 10ms for 100Hz)

    /// Record a period measurement
    void recordPeriod(uint32_t period_us) {
        if (period_us < min_period_us) min_period_us = period_us;
        if (period_us > max_period_us) max_period_us = period_us;

        // Check for jitter violation
        int32_t deviation = static_cast<int32_t>(period_us) -
                           static_cast<int32_t>(target_period_us);
        if (deviation < 0) deviation = -deviation;
        if (static_cast<uint32_t>(deviation) > RT_JITTER_WARN_US) {
            jitter_violations++;
        }
    }

    /// Get peak-to-peak jitter
    uint32_t jitter_us() const {
        if (min_period_us == UINT32_MAX) return 0;
        return max_period_us - min_period_us;
    }

    /// Reset statistics
    void reset() {
        min_period_us = UINT32_MAX;
        max_period_us = 0;
        jitter_violations = 0;
    }
};

} // namespace mara

// =============================================================================
// Function annotations for documentation
// =============================================================================

// =============================================================================
// Allocation zone markers
// =============================================================================

/**
 * ALLOC_SETUP - Code runs in setup phase, allocation is allowed.
 */
#define ALLOC_SETUP /* setup phase - allocation allowed */

/**
 * ALLOC_FORBIDDEN - Code runs in hot path, allocation is forbidden.
 */
#define ALLOC_FORBIDDEN /* hot path - no allocation */

/**
 * ALLOC_BOUNDED - Code may allocate with bounded size (e.g., JsonDocument).
 */
#define ALLOC_BOUNDED /* bounded allocation - telemetry/handlers */

// =============================================================================
// Function annotations for documentation
// =============================================================================

/**
 * RT_SAFE - Mark a function as real-time safe.
 * Function guarantees no heap allocation, no blocking, bounded execution.
 * Used for documentation - helps identify which functions can be called from control loop.
 */
#define RT_SAFE /* real-time safe - no heap, no blocking */

/**
 * RT_UNSAFE - Mark a function as NOT real-time safe.
 * Function may allocate, block, or have unbounded execution time.
 * Must NOT be called from control loop or safety loop.
 */
#define RT_UNSAFE /* not real-time safe - may allocate or block */

/**
 * RT_ISR - Mark a function as ISR-safe.
 * Even stricter than RT_SAFE: no FreeRTOS calls, minimal code.
 */
#define RT_ISR /* ISR context - minimal operations only */

/**
 * RT_MAX_US(x) - Document maximum execution time in microseconds.
 * Use with RT_SAFE functions to document timing contract.
 * Example: RT_SAFE RT_MAX_US(500) void step();
 */
#define RT_MAX_US(x) /* max execution time: x microseconds */

// =============================================================================
// Heap check macros for development debugging
// =============================================================================

// Enable/disable runtime heap checking (set to 0 for release builds)
#ifndef RT_HEAP_CHECK_ENABLED
#define RT_HEAP_CHECK_ENABLED 1
#endif

// Threshold in bytes - allocations smaller than this are ignored
#define RT_HEAP_CHECK_THRESHOLD 64

#if defined(ARDUINO) && defined(ESP32) && RT_HEAP_CHECK_ENABLED
#include <esp_heap_caps.h>

/**
 * Mark entry to real-time critical section.
 * Records current heap size for later comparison.
 */
#define RT_CONTROL_ENTER() \
    const size_t __rt_heap_start = heap_caps_get_free_size(MALLOC_CAP_DEFAULT)

/**
 * Check heap at exit from real-time critical section.
 * Warns if heap decreased (allocation occurred) by more than threshold.
 */
#define RT_CONTROL_EXIT_CHECK(name) \
    do { \
        size_t __rt_heap_end = heap_caps_get_free_size(MALLOC_CAP_DEFAULT); \
        if (__rt_heap_end < __rt_heap_start - RT_HEAP_CHECK_THRESHOLD) { \
            Serial.printf("[RT_WARN] %s allocated %d bytes\n", \
                          name, (int)(__rt_heap_start - __rt_heap_end)); \
        } \
    } while(0)

/**
 * Assert no allocation occurred - for stricter checking.
 * Use in debug builds to catch any allocation.
 */
#define RT_ASSERT_NO_ALLOC(name) \
    do { \
        size_t __rt_heap_end = heap_caps_get_free_size(MALLOC_CAP_DEFAULT); \
        if (__rt_heap_end < __rt_heap_start) { \
            Serial.printf("[RT_FAIL] %s allocated %d bytes - RT violation!\n", \
                          name, (int)(__rt_heap_start - __rt_heap_end)); \
        } \
    } while(0)

#else
// No-op for non-ESP32 builds (native tests) or disabled
#define RT_CONTROL_ENTER() ((void)0)
#define RT_CONTROL_EXIT_CHECK(name) ((void)0)
#define RT_ASSERT_NO_ALLOC(name) ((void)0)
#endif

// =============================================================================
// HAL-based heap check macros (portable)
// =============================================================================

/**
 * HAL-based entry to real-time critical section.
 * Uses IHeapMonitor interface for portability.
 * @param hal Pointer to IHeapMonitor (can be nullptr)
 */
#define RT_CONTROL_ENTER_HAL(hal) \
    const size_t __rt_heap_start = ((hal) ? (hal)->getFreeSize(::hal::MemoryCaps::Default) : 0)

/**
 * HAL-based check at exit from real-time critical section.
 * @param hal Pointer to IHeapMonitor (can be nullptr)
 * @param name Name of the zone for logging
 */
#define RT_CONTROL_EXIT_CHECK_HAL(hal, name) \
    do { \
        if (hal) { \
            size_t __rt_heap_end = (hal)->getFreeSize(::hal::MemoryCaps::Default); \
            if (__rt_heap_end < __rt_heap_start - RT_HEAP_CHECK_THRESHOLD) { \
                Serial.printf("[RT_WARN] %s allocated %d bytes\n", \
                              name, (int)(__rt_heap_start - __rt_heap_end)); \
            } \
        } \
    } while(0)

// =============================================================================
// Real-time zone macros (for explicit scoping)
// =============================================================================

/**
 * Begin a real-time critical zone.
 * All code until RT_ZONE_END must be RT_SAFE.
 */
#define RT_ZONE_BEGIN(name) \
    RT_CONTROL_ENTER(); \
    const char* __rt_zone_name = name

/**
 * End a real-time critical zone and check for violations.
 */
#define RT_ZONE_END() \
    RT_CONTROL_EXIT_CHECK(__rt_zone_name)
