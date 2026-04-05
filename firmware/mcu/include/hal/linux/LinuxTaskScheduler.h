// include/hal/linux/LinuxTaskScheduler.h
// Linux task scheduler implementation using pthreads
//
// Provides RTOS-like task management for Linux systems.
// Supports real-time scheduling via SCHED_FIFO (requires CAP_SYS_NICE).
#pragma once

#include "../ITaskScheduler.h"
#include <cstdint>
#include <map>
#include <mutex>
#include <atomic>
#include <pthread.h>
#include <ctime>

namespace hal {

/// Linux task scheduler using pthreads
///
/// Provides task creation and scheduling similar to FreeRTOS:
/// - Priority-based scheduling via SCHED_FIFO (if permitted)
/// - Precise periodic timing via clock_nanosleep
/// - Core affinity support on multi-core systems
///
/// Note: Real-time scheduling requires CAP_SYS_NICE capability:
///   sudo setcap cap_sys_nice+ep ./your_binary
class LinuxTaskScheduler : public ITaskScheduler {
public:
    LinuxTaskScheduler();
    ~LinuxTaskScheduler();

    bool createTask(TaskFunction func, void* param,
                   const TaskConfig& config, TaskHandle& outHandle) override;

    void deleteTask(TaskHandle handle) override;
    void deleteCurrentTask() override;

    void delay(uint32_t ticks) override;
    void delayMs(uint32_t ms) override;
    void delayUntil(uint32_t& previousWakeTime, uint32_t periodTicks) override;

    uint32_t getTickCount() override;
    uint32_t msToTicks(uint32_t ms) override;
    uint32_t ticksToMs(uint32_t ticks) override;

    uint8_t getCurrentCore() override;
    TaskHandle getCurrentTask() override;
    void suspendTask(TaskHandle handle) override;
    void resumeTask(TaskHandle handle) override;

private:
    struct TaskInfo {
        pthread_t thread;
        TaskFunction func;
        void* param;
        const char* name;
        std::atomic<bool> running{true};
        std::atomic<bool> suspended{false};
        pthread_mutex_t suspendMutex;
        pthread_cond_t suspendCond;
    };

    std::map<pthread_t, TaskInfo*> tasks_;
    std::mutex tasksMutex_;
    struct timespec bootTime_;
    std::atomic<uint32_t> taskIdCounter_{0};

    // Thread-local storage for current task tracking
    static thread_local TaskInfo* currentTask_;

    static void* threadWrapper(void* arg);
    bool setRealTimePriority(pthread_t thread, uint8_t priority);
    bool setCoreAffinity(pthread_t thread, int8_t core);
};

} // namespace hal
