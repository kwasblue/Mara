#include "hal/esp32/Esp32TaskScheduler.h"
#include <Arduino.h>

namespace hal {

bool Esp32TaskScheduler::createTask(TaskFunction func, void* param,
                                    const TaskConfig& config, TaskHandle& outHandle) {
    TaskHandle_t taskHandle = nullptr;
    BaseType_t result;

    if (config.core >= 0) {
        // Pin to specific core
        result = xTaskCreatePinnedToCore(
            func,
            config.name,
            config.stackSize,
            param,
            config.priority,
            &taskHandle,
            config.core
        );
    } else {
        // No core affinity
        result = xTaskCreate(
            func,
            config.name,
            config.stackSize,
            param,
            config.priority,
            &taskHandle
        );
    }

    if (result == pdPASS && taskHandle != nullptr) {
        outHandle.native = taskHandle;
        return true;
    }

    outHandle.native = nullptr;
    return false;
}

void Esp32TaskScheduler::deleteTask(TaskHandle handle) {
    // NOTE: vTaskDelete on a task running on another core is legal in FreeRTOS,
    // but the deleted task's stack and TCB aren't freed until the idle task runs
    // on that core. Callers should ensure the task has exited its critical work
    // (e.g., by setting a stop flag and waiting briefly) before calling deleteTask
    // to avoid races with stack/context cleanup.
    if (handle.native != nullptr) {
        vTaskDelete(static_cast<TaskHandle_t>(handle.native));
    }
}

void Esp32TaskScheduler::deleteCurrentTask() {
    vTaskDelete(nullptr);
}

void Esp32TaskScheduler::delay(uint32_t ticks) {
    vTaskDelay(ticks);
}

void Esp32TaskScheduler::delayMs(uint32_t ms) {
    vTaskDelay(pdMS_TO_TICKS(ms));
}

void Esp32TaskScheduler::delayUntil(uint32_t& previousWakeTime, uint32_t periodTicks) {
    TickType_t lastWake = static_cast<TickType_t>(previousWakeTime);
    vTaskDelayUntil(&lastWake, periodTicks);
    previousWakeTime = static_cast<uint32_t>(lastWake);
}

uint32_t Esp32TaskScheduler::getTickCount() {
    return xTaskGetTickCount();
}

uint32_t Esp32TaskScheduler::msToTicks(uint32_t ms) {
    return pdMS_TO_TICKS(ms);
}

uint32_t Esp32TaskScheduler::ticksToMs(uint32_t ticks) {
    return ticks * portTICK_PERIOD_MS;
}

uint8_t Esp32TaskScheduler::getCurrentCore() {
    return xPortGetCoreID();
}

TaskHandle Esp32TaskScheduler::getCurrentTask() {
    TaskHandle handle;
    handle.native = xTaskGetCurrentTaskHandle();
    return handle;
}

void Esp32TaskScheduler::suspendTask(TaskHandle handle) {
    if (handle.native != nullptr) {
        vTaskSuspend(static_cast<TaskHandle_t>(handle.native));
    } else {
        vTaskSuspend(nullptr);  // Suspend self
    }
}

void Esp32TaskScheduler::resumeTask(TaskHandle handle) {
    if (handle.native != nullptr) {
        vTaskResume(static_cast<TaskHandle_t>(handle.native));
    }
}

} // namespace hal
