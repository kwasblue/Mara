#pragma once

#include "../ITaskScheduler.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

namespace hal {

/// ESP32 task scheduler implementation using FreeRTOS
class Esp32TaskScheduler : public ITaskScheduler {
public:
    Esp32TaskScheduler() = default;
    ~Esp32TaskScheduler() = default;

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
};

} // namespace hal
