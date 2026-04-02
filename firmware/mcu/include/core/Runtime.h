// include/core/Runtime.h
// Top-level runtime orchestrator for ESP32 MCU Host
//
// Usage:
//   static mara::Runtime runtime;
//   void setup() { runtime.setup(); }
//   void loop()  { runtime.loop(); }
//
// The Runtime class:
//   - Owns all service storage (ServiceStorage)
//   - Manages initialization order and dependencies
//   - Provides the main loop with proper scheduling
//   - Handles critical failures gracefully

#pragma once

#include "core/ServiceStorage.h"
#include "core/ServiceContext.h"
#include "core/LoopTiming.h"
#include "core/LoopRates.h"
#include "setup/SetupModules.h"

namespace mara {

/// Runtime configuration
struct RuntimeConfig {
    // Serial
    uint32_t serial_baud = 115200;

    // Networking
    uint16_t tcp_port = 3333;

    // Device identity
    const char* device_name = "ESP32-bot";

    // Note: safety_hz is configured via MaraConfig.rates.safety_hz (single source of truth)

    // Control task (FreeRTOS)
    bool use_freertos_control = true;
    uint16_t control_rate_hz = 100;
    uint16_t control_stack_size = 4096;
    uint8_t control_priority = 5;
    uint8_t control_core = 1;
};

/// Top-level runtime orchestrator
/// Wires all services and manages the main loop
class Runtime {
public:
    Runtime() = default;

    /// Initialize the runtime with configuration
    /// Call from Arduino setup()
    bool setup(const RuntimeConfig& config = RuntimeConfig{});

    /// Run one iteration of the main loop
    /// Call from Arduino loop()
    void loop();

    /// Check if runtime is in critical failure state
    bool hasCriticalFailure() const { return criticalFailure_; }

    /// Get service context for external access
    ServiceContext& context() { return ctx_; }
    const ServiceContext& context() const { return ctx_; }

    /// Get raw storage for advanced use cases
    ServiceStorage& storage() { return storage_; }

private:
    ServiceStorage storage_;
    ServiceContext ctx_;
    RuntimeConfig config_;

    bool criticalFailure_ = false;
    bool controlTaskStarted_ = false;

    // Setup module pointers
    static constexpr size_t MAX_SETUP_MODULES = 8;
    ISetupModule* setupModules_[MAX_SETUP_MODULES] = {nullptr};
    size_t numSetupModules_ = 0;

    // Internal methods
    bool initializeStorage();
    bool runSetupModules();
    bool startControlTask();
    void updateLoopSchedulers();
    void runMainLoop(uint32_t now_ms);
};

} // namespace mara
