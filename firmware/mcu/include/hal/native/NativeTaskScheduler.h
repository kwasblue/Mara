// include/hal/native/NativeTaskScheduler.h
// Native task scheduler implementation for testing
// Provides a cooperative single-threaded stub for native builds
#pragma once

#include "../ITaskScheduler.h"
#include <cstdint>

namespace hal {

/// Native task scheduler stub for testing.
/// This is NOT a real task scheduler - it provides minimal
/// cooperative behavior for native unit tests.
///
/// Tasks are NOT actually created in parallel. Instead:
/// - createTask() stores the function but does NOT execute it
/// - For testing, call runTask() manually to execute
/// - delay functions advance a fake tick counter
///
/// This allows testing code that uses the scheduler interface
/// without requiring FreeRTOS.
class NativeTaskScheduler : public ITaskScheduler {
public:
    NativeTaskScheduler() = default;

    bool createTask(TaskFunction func, void* param,
                   const TaskConfig& config, TaskHandle& outHandle) override {
        // Store the task info for potential manual invocation
        if (taskCount_ >= MAX_TASKS) {
            return false;
        }
        tasks_[taskCount_].func = func;
        tasks_[taskCount_].param = param;
        tasks_[taskCount_].name = config.name;
        outHandle.native = reinterpret_cast<void*>(taskCount_ + 1);
        taskCount_++;
        return true;
    }

    void deleteTask(TaskHandle handle) override {
        // Mark task as deleted (no-op for stub)
        (void)handle;
    }

    void deleteCurrentTask() override {
        // No-op in native - would just return from function
    }

    void delay(uint32_t ticks) override {
        tickCount_ += ticks;
    }

    void delayMs(uint32_t ms) override {
        tickCount_ += ms;  // Assuming 1 tick = 1 ms for simplicity
    }

    void delayUntil(uint32_t& previousWakeTime, uint32_t periodTicks) override {
        // Advance to next period boundary
        previousWakeTime += periodTicks;
        if (tickCount_ < previousWakeTime) {
            tickCount_ = previousWakeTime;
        }
    }

    uint32_t getTickCount() override {
        return tickCount_;
    }

    uint32_t msToTicks(uint32_t ms) override {
        return ms;  // 1:1 for native
    }

    uint32_t ticksToMs(uint32_t ticks) override {
        return ticks;  // 1:1 for native
    }

    uint8_t getCurrentCore() override {
        return 0;  // Single core for native
    }

    TaskHandle getCurrentTask() override {
        return currentTask_;
    }

    void suspendTask(TaskHandle handle) override {
        (void)handle;  // No-op for native
    }

    void resumeTask(TaskHandle handle) override {
        (void)handle;  // No-op for native
    }

    // =========================================================================
    // Test helpers (not part of ITaskScheduler interface)
    // =========================================================================

    /// Manually run a task once (for testing)
    void runTask(TaskHandle handle) {
        size_t idx = reinterpret_cast<size_t>(handle.native) - 1;
        if (idx < taskCount_ && tasks_[idx].func) {
            currentTask_ = handle;
            tasks_[idx].func(tasks_[idx].param);
            currentTask_.native = nullptr;
        }
    }

    /// Set the tick count (for testing timing scenarios)
    void setTickCount(uint32_t ticks) {
        tickCount_ = ticks;
    }

    /// Get number of tasks created
    size_t getTaskCount() const {
        return taskCount_;
    }

    /// Reset scheduler state
    void reset() {
        taskCount_ = 0;
        tickCount_ = 0;
        currentTask_.native = nullptr;
    }

private:
    static constexpr size_t MAX_TASKS = 8;

    struct TaskInfo {
        TaskFunction func = nullptr;
        void* param = nullptr;
        const char* name = nullptr;
    };

    TaskInfo tasks_[MAX_TASKS] = {};
    size_t taskCount_ = 0;
    uint32_t tickCount_ = 0;
    TaskHandle currentTask_;
};

} // namespace hal
