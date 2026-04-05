// src/hal/linux/LinuxTaskScheduler.cpp
// Linux task scheduler implementation using pthreads

#include "hal/linux/LinuxTaskScheduler.h"

#if PLATFORM_LINUX

#include <sched.h>
#include <unistd.h>
#include <cstring>

namespace hal {

// Thread-local storage for current task
thread_local LinuxTaskScheduler::TaskInfo* LinuxTaskScheduler::currentTask_ = nullptr;

LinuxTaskScheduler::LinuxTaskScheduler() {
    clock_gettime(CLOCK_MONOTONIC, &bootTime_);
}

LinuxTaskScheduler::~LinuxTaskScheduler() {
    // Stop all tasks
    std::lock_guard<std::mutex> lock(tasksMutex_);
    for (auto& [thread, info] : tasks_) {
        info->running = false;
        if (info->suspended) {
            pthread_mutex_lock(&info->suspendMutex);
            info->suspended = false;
            pthread_cond_signal(&info->suspendCond);
            pthread_mutex_unlock(&info->suspendMutex);
        }
    }

    // Wait for all tasks to finish
    for (auto& [thread, info] : tasks_) {
        pthread_join(thread, nullptr);
        pthread_mutex_destroy(&info->suspendMutex);
        pthread_cond_destroy(&info->suspendCond);
        delete info;
    }
    tasks_.clear();
}

bool LinuxTaskScheduler::createTask(TaskFunction func, void* param,
                                     const TaskConfig& config, TaskHandle& outHandle) {
    std::lock_guard<std::mutex> lock(tasksMutex_);

    auto* info = new TaskInfo();
    info->func = func;
    info->param = param;
    info->name = config.name;
    info->running = true;
    info->suspended = false;
    pthread_mutex_init(&info->suspendMutex, nullptr);
    pthread_cond_init(&info->suspendCond, nullptr);

    pthread_attr_t attr;
    pthread_attr_init(&attr);

    // Set stack size
    if (config.stackSize > 0) {
        pthread_attr_setstacksize(&attr, config.stackSize);
    }

    // Create thread
    pthread_t thread;
    int rc = pthread_create(&thread, &attr, threadWrapper, info);
    pthread_attr_destroy(&attr);

    if (rc != 0) {
        delete info;
        return false;
    }

    // Try to set real-time priority (requires privileges)
    if (config.priority > 0) {
        setRealTimePriority(thread, config.priority);
    }

    // Try to set core affinity
    if (config.core >= 0) {
        setCoreAffinity(thread, config.core);
    }

    tasks_[thread] = info;
    outHandle.native = reinterpret_cast<void*>(thread);

    return true;
}

void LinuxTaskScheduler::deleteTask(TaskHandle handle) {
    if (!handle.native) {
        deleteCurrentTask();
        return;
    }

    pthread_t thread = reinterpret_cast<pthread_t>(handle.native);

    std::lock_guard<std::mutex> lock(tasksMutex_);
    auto it = tasks_.find(thread);
    if (it == tasks_.end()) {
        return;
    }

    TaskInfo* info = it->second;
    info->running = false;

    // Wake up if suspended
    pthread_mutex_lock(&info->suspendMutex);
    info->suspended = false;
    pthread_cond_signal(&info->suspendCond);
    pthread_mutex_unlock(&info->suspendMutex);

    // Wait for thread to finish
    tasksMutex_.unlock();
    pthread_join(thread, nullptr);
    tasksMutex_.lock();

    pthread_mutex_destroy(&info->suspendMutex);
    pthread_cond_destroy(&info->suspendCond);
    delete info;
    tasks_.erase(thread);
}

void LinuxTaskScheduler::deleteCurrentTask() {
    pthread_t self = pthread_self();

    {
        std::lock_guard<std::mutex> lock(tasksMutex_);
        auto it = tasks_.find(self);
        if (it != tasks_.end()) {
            it->second->running = false;
        }
    }

    pthread_exit(nullptr);
}

void LinuxTaskScheduler::delay(uint32_t ticks) {
    delayMs(ticksToMs(ticks));
}

void LinuxTaskScheduler::delayMs(uint32_t ms) {
    // Check for suspension
    if (currentTask_ && currentTask_->suspended) {
        pthread_mutex_lock(&currentTask_->suspendMutex);
        while (currentTask_->suspended && currentTask_->running) {
            pthread_cond_wait(&currentTask_->suspendCond, &currentTask_->suspendMutex);
        }
        pthread_mutex_unlock(&currentTask_->suspendMutex);
    }

    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000L;
    clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, nullptr);
}

void LinuxTaskScheduler::delayUntil(uint32_t& previousWakeTime, uint32_t periodTicks) {
    // Calculate next wake time
    previousWakeTime += periodTicks;

    // Convert to absolute timespec
    struct timespec ts;
    ts.tv_sec = bootTime_.tv_sec + (previousWakeTime / 1000);
    ts.tv_nsec = bootTime_.tv_nsec + ((previousWakeTime % 1000) * 1000000L);

    // Normalize
    while (ts.tv_nsec >= 1000000000L) {
        ts.tv_nsec -= 1000000000L;
        ts.tv_sec++;
    }

    // Check for suspension
    if (currentTask_ && currentTask_->suspended) {
        pthread_mutex_lock(&currentTask_->suspendMutex);
        while (currentTask_->suspended && currentTask_->running) {
            pthread_cond_wait(&currentTask_->suspendCond, &currentTask_->suspendMutex);
        }
        pthread_mutex_unlock(&currentTask_->suspendMutex);
    }

    // Sleep until absolute time
    clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, nullptr);
}

uint32_t LinuxTaskScheduler::getTickCount() {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);

    uint64_t elapsed_ms = (now.tv_sec - bootTime_.tv_sec) * 1000ULL +
                          (now.tv_nsec - bootTime_.tv_nsec) / 1000000ULL;
    return static_cast<uint32_t>(elapsed_ms);
}

uint32_t LinuxTaskScheduler::msToTicks(uint32_t ms) {
    return ms;  // 1:1 on Linux
}

uint32_t LinuxTaskScheduler::ticksToMs(uint32_t ticks) {
    return ticks;  // 1:1 on Linux
}

uint8_t LinuxTaskScheduler::getCurrentCore() {
    return static_cast<uint8_t>(sched_getcpu());
}

TaskHandle LinuxTaskScheduler::getCurrentTask() {
    TaskHandle handle;
    handle.native = reinterpret_cast<void*>(pthread_self());
    return handle;
}

void LinuxTaskScheduler::suspendTask(TaskHandle handle) {
    pthread_t thread = handle.native ? reinterpret_cast<pthread_t>(handle.native)
                                     : pthread_self();

    std::lock_guard<std::mutex> lock(tasksMutex_);
    auto it = tasks_.find(thread);
    if (it != tasks_.end()) {
        it->second->suspended = true;
    }
}

void LinuxTaskScheduler::resumeTask(TaskHandle handle) {
    pthread_t thread = reinterpret_cast<pthread_t>(handle.native);

    std::lock_guard<std::mutex> lock(tasksMutex_);
    auto it = tasks_.find(thread);
    if (it != tasks_.end()) {
        pthread_mutex_lock(&it->second->suspendMutex);
        it->second->suspended = false;
        pthread_cond_signal(&it->second->suspendCond);
        pthread_mutex_unlock(&it->second->suspendMutex);
    }
}

void* LinuxTaskScheduler::threadWrapper(void* arg) {
    TaskInfo* info = static_cast<TaskInfo*>(arg);
    currentTask_ = info;

    while (info->running) {
        // Check suspension
        pthread_mutex_lock(&info->suspendMutex);
        while (info->suspended && info->running) {
            pthread_cond_wait(&info->suspendCond, &info->suspendMutex);
        }
        pthread_mutex_unlock(&info->suspendMutex);

        if (!info->running) break;

        // Run the task function
        if (info->func) {
            info->func(info->param);
        }

        // Task function returned, exit
        break;
    }

    currentTask_ = nullptr;
    return nullptr;
}

bool LinuxTaskScheduler::setRealTimePriority(pthread_t thread, uint8_t priority) {
    struct sched_param param;
    param.sched_priority = priority;

    // Try SCHED_FIFO (requires CAP_SYS_NICE)
    if (pthread_setschedparam(thread, SCHED_FIFO, &param) == 0) {
        return true;
    }

    // Fall back to regular priority via nice (limited range)
    // Note: This won't work well for real-time requirements
    return false;
}

bool LinuxTaskScheduler::setCoreAffinity(pthread_t thread, int8_t core) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core, &cpuset);

    return pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) == 0;
}

} // namespace hal

#endif // PLATFORM_LINUX
