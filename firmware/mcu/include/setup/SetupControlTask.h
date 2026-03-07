#pragma once

#include <cstdint>

namespace mara {

struct ServiceContext;

/// Configuration for the FreeRTOS control task
struct ControlTaskConfig {
    uint16_t rate_hz = 100;         // Control loop rate (default 100Hz)
    uint16_t stack_size = 4096;     // Stack size in bytes
    uint8_t priority = 5;           // Task priority (0-24, higher = more priority)
    uint8_t core = 1;               // Core to run on (0 or 1, 1 recommended - Core 0 is WiFi)
};

/// Start the FreeRTOS control task
/// @param ctx Service context (must remain valid for lifetime of task)
/// @param config Task configuration
/// @return true if task started successfully
bool startControlTask(ServiceContext& ctx, const ControlTaskConfig& config = {});

/// Stop the control task (if running)
void stopControlTask();

/// Check if control task is running
bool isControlTaskRunning();

/// Get control task timing statistics
struct ControlTaskStats {
    uint32_t iterations = 0;
    uint32_t max_exec_us = 0;
    uint32_t overruns = 0;          // Times loop exceeded period
    uint32_t last_exec_us = 0;
    // Jitter tracking
    uint32_t min_period_us = 0;     // Minimum observed period between iterations
    uint32_t max_period_us = 0;     // Maximum observed period between iterations
    uint32_t jitter_violations = 0; // Count of periods deviating > 500us from target
};
ControlTaskStats getControlTaskStats();

/// Reset control task statistics
void resetControlTaskStats();

} // namespace mara
