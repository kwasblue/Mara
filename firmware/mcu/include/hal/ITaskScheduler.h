#pragma once

#include <cstdint>

namespace hal {

/// Task function signature
/// @param param User parameter passed to createTask
using TaskFunction = void (*)(void* param);

/// Opaque task handle
/// Platform implementations store their native handle internally
struct TaskHandle {
    void* native = nullptr;  // Platform-specific handle (TaskHandle_t, etc.)
};

/// Task configuration
struct TaskConfig {
    const char* name = "task";      // Task name (for debugging)
    uint32_t stackSize = 4096;      // Stack size in bytes
    uint8_t priority = 5;           // Priority (0 = lowest, higher = more priority)
    int8_t core = -1;               // Core affinity (-1 = no affinity, 0/1 = specific core)
};

/// Abstract task scheduler interface for platform portability
/// Provides RTOS task management functions.
///
/// Usage:
///   ITaskScheduler* scheduler = hal.scheduler;
///
///   TaskConfig cfg;
///   cfg.name = "ControlTask";
///   cfg.stackSize = 4096;
///   cfg.priority = 5;
///   cfg.core = 1;
///
///   TaskHandle handle;
///   if (scheduler->createTask(taskFunc, &ctx, cfg, handle)) {
///       // Task running
///   }
///
///   // In task function:
///   uint32_t lastWake = scheduler->getTickCount();
///   for (;;) {
///       // ... work ...
///       scheduler->delayUntil(lastWake, periodTicks);
///   }
///
/// Notes:
///   - delayUntil provides precise periodic timing
///   - On single-core systems, core affinity is ignored
class ITaskScheduler {
public:
    virtual ~ITaskScheduler() = default;

    // =========================================================================
    // Task creation/deletion
    // =========================================================================

    /// Create a new task
    /// @param func Task function to execute
    /// @param param Parameter passed to task function
    /// @param config Task configuration
    /// @param outHandle Output: handle to created task
    /// @return true if task created successfully
    virtual bool createTask(TaskFunction func, void* param,
                           const TaskConfig& config, TaskHandle& outHandle) = 0;

    /// Delete a task
    /// @param handle Task handle (from createTask), or null handle to delete self
    virtual void deleteTask(TaskHandle handle) = 0;

    /// Delete the calling task (task deletes itself)
    virtual void deleteCurrentTask() = 0;

    // =========================================================================
    // Delay functions
    // =========================================================================

    /// Delay for specified number of ticks
    /// @param ticks Number of ticks to delay
    virtual void delay(uint32_t ticks) = 0;

    /// Delay for specified milliseconds
    /// @param ms Milliseconds to delay
    virtual void delayMs(uint32_t ms) = 0;

    /// Delay until specified tick count (for precise periodic timing)
    /// @param previousWakeTime Reference tick count (updated by this function)
    /// @param periodTicks Period in ticks
    virtual void delayUntil(uint32_t& previousWakeTime, uint32_t periodTicks) = 0;

    // =========================================================================
    // Tick/time utilities
    // =========================================================================

    /// Get current tick count
    /// @return Current tick count
    virtual uint32_t getTickCount() = 0;

    /// Convert milliseconds to ticks
    /// @param ms Milliseconds
    /// @return Equivalent tick count
    virtual uint32_t msToTicks(uint32_t ms) = 0;

    /// Convert ticks to milliseconds
    /// @param ticks Tick count
    /// @return Equivalent milliseconds
    virtual uint32_t ticksToMs(uint32_t ticks) = 0;

    // =========================================================================
    // Task queries
    // =========================================================================

    /// Get current core ID (for multi-core systems)
    /// @return Core number (0 or 1), 0 on single-core
    virtual uint8_t getCurrentCore() = 0;

    /// Get the handle of the currently running task
    /// @return Handle to current task
    virtual TaskHandle getCurrentTask() = 0;

    /// Suspend a task
    /// @param handle Task to suspend (null = suspend self)
    virtual void suspendTask(TaskHandle handle) = 0;

    /// Resume a suspended task
    /// @param handle Task to resume
    virtual void resumeTask(TaskHandle handle) = 0;
};

} // namespace hal
