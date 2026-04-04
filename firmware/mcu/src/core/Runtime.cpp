// src/core/Runtime.cpp
// Runtime orchestrator implementation - platform-agnostic

#include "core/Runtime.h"
#include "config/PlatformConfig.h"
#include "setup/SetupControlTask.h"
#include "loop/LoopFunctions.h"
#include "sensor/SensorRegistry.h"
#include "core/Clock.h"
#include "config/MaraConfig.h"

// Platform-specific includes (guarded)
#if PLATFORM_HAS_ARDUINO
#include <Arduino.h>
#endif

namespace mara {

bool Runtime::setup(const RuntimeConfig& config) {
    config_ = config;

    // Platform-specific serial initialization
#if PLATFORM_HAS_ARDUINO
    Serial.begin(config_.serial_baud);
#endif

    // Wire HAL to managers first
    storage_.initHal();

    // Build HAL context for logging
    auto halCtx = storage_.hal.buildContext();

    // Set up debug logger and clock
    setDebugLogger(halCtx.logger);
    setHalClock(halCtx.clock);

    // Initial boot delay via HAL
    if (halCtx.clock) {
        halCtx.clock->delayMs(500);
    }

    if (halCtx.logger) {
        halCtx.logger->println("\n[Runtime] Booting...");
    }

    // Phase 1: Initialize storage components
    if (!initializeStorage()) {
        if (halCtx.logger) {
            halCtx.logger->println("[Runtime] FATAL: Storage initialization failed");
        }
        criticalFailure_ = true;
        return false;
    }

    // Phase 2: Run setup modules
    if (!runSetupModules()) {
        // Critical failure already logged
        return false;
    }

    // Phase 3: Start FreeRTOS control task (if enabled)
    if (config_.use_freertos_control) {
        if (!startControlTask()) {
            if (halCtx.logger) {
                halCtx.logger->println("[Runtime] WARNING: Control task failed, using cooperative scheduling");
            }
        }
    }

    // Phase 4: Final wiring
    if (ctx_.host) {
        if (ctx_.control) {
            ctx_.host->addModule(ctx_.control);
        }
        if (ctx_.heartbeat) {
            ctx_.host->addModule(ctx_.heartbeat);
        }
    }

    updateLoopSchedulers();

    if (halCtx.logger) {
        halCtx.logger->println("[Runtime] Setup complete");
        LoopRates& r = getLoopRates();
        halCtx.logger->printf("[Runtime] Loop rates: ctrl=%dHz safety=%dHz telem=%dHz\n",
                      r.ctrl_hz, r.safety_hz, r.telem_hz);
    }

    return true;
}

void Runtime::loop() {
    if (criticalFailure_) {
        auto halCtx = storage_.hal.buildContext();
        if (halCtx.clock) {
            halCtx.clock->delayMs(100);
        }
        return;
    }

    uint32_t now_ms = getSystemClock().millis();
    runMainLoop(now_ms);
}

bool Runtime::initializeStorage() {
    // Configure transports using HAL config structs
#if PLATFORM_HAS_ARDUINO
    hal::UartTransportConfig uartCfg{&Serial, config_.serial_baud};
#else
    hal::UartTransportConfig uartCfg{nullptr, config_.serial_baud};
#endif
    hal::WifiTransportConfig wifiCfg{config_.tcp_port};
    storage_.initTransports(uartCfg, wifiCfg);
    storage_.initRouter();
    storage_.initCommands();
    storage_.initControl();
    storage_.initHost(config_.device_name);

    ctx_ = storage_.buildContext();

    // Initialize handlers with dependencies (must be after buildContext)
    storage_.initHandlers(ctx_);

    return true;
}

bool Runtime::runSetupModules() {
    auto halCtx = storage_.hal.buildContext();

    // Populate setup modules
    setupModules_[0] = getSetupWifiModule();
    setupModules_[1] = getSetupOtaModule();
    setupModules_[2] = getSetupSafetyModule();
    setupModules_[3] = getSetupMotorsModule();
    setupModules_[4] = getSetupSensorsModule();
    setupModules_[5] = getSetupTransportModule();
    setupModules_[6] = getSetupTelemetryModule();
    numSetupModules_ = 7;

    for (size_t i = 0; i < numSetupModules_; ++i) {
        ISetupModule* mod = setupModules_[i];
        if (!mod) continue;

        auto result = mod->setup(ctx_);
        if (result.isError()) {
            if (halCtx.logger) {
                halCtx.logger->printf("[%s] FAILED: %s\n",
                              mod->name(),
                              errorCodeToString(result.errorCode()));
            }

            if (mod->isCritical()) {
                if (halCtx.logger) {
                    halCtx.logger->printf("[Runtime] FATAL: Critical module '%s' failed\n", mod->name());
                }
                criticalFailure_ = true;

                if (ctx_.dcMotor) ctx_.dcMotor->stopAll();

                // Don't return - let remaining modules run for diagnostics
                // The criticalFailure_ flag will prevent further phases from running
            }
        }
    }

    return !criticalFailure_;
}

bool Runtime::startControlTask() {
    auto halCtx = storage_.hal.buildContext();

    ControlTaskConfig taskCfg;
    taskCfg.rate_hz = config_.control_rate_hz;
    taskCfg.stack_size = config_.control_stack_size;
    taskCfg.priority = config_.control_priority;
    taskCfg.core = config_.control_core;

    controlTaskStarted_ = mara::startControlTask(ctx_, taskCfg);
    if (controlTaskStarted_ && halCtx.logger) {
        halCtx.logger->println("[Runtime] FreeRTOS control task started");
    }
    return controlTaskStarted_;
}

void Runtime::updateLoopSchedulers() {
    LoopRates& r = getLoopRates();
    if (ctx_.safetyScheduler) {
        ctx_.safetyScheduler->setPeriodMs(r.safety_period_ms());
    }
    if (ctx_.controlScheduler) {
        ctx_.controlScheduler->setPeriodMs(r.ctrl_period_ms());
    }
    if (ctx_.telemetryScheduler) {
        ctx_.telemetryScheduler->setPeriodMs(r.telem_period_ms());
    }
}

void Runtime::runMainLoop(uint32_t now_ms) {
    uint32_t loop_start_us = getSystemClock().micros();
    LoopTiming& timing = getLoopTiming();

    // OTA handling via HAL
#if HAS_OTA
    auto halCtx = storage_.hal.buildContext();
    if (halCtx.ota) {
        halCtx.ota->handle();
    }
#endif

    // Update scheduler periods (in case rates changed via command)
    updateLoopSchedulers();

    // Rate-limited safety loop
    if (ctx_.safetyScheduler && ctx_.safetyScheduler->tick(now_ms)) {
        uint32_t t0 = getSystemClock().micros();
        runSafetyLoop(ctx_, now_ms);
        timing.safety_us = getSystemClock().micros() - t0;
    }

    // Rate-limited control loop (skip if FreeRTOS task is handling it)
    if (!isControlTaskRunning()) {
        if (ctx_.controlScheduler && ctx_.controlScheduler->tick(now_ms)) {
            uint32_t t0 = getSystemClock().micros();
            float ctrl_dt = getLoopRates().ctrl_period_ms() / 1000.0f;
            runControlLoop(ctx_, now_ms, ctrl_dt);
            timing.control_us = getSystemClock().micros() - t0;
        }
    } else {
        ControlTaskStats taskStats = getControlTaskStats();
        timing.control_us = taskStats.last_exec_us;
        if (taskStats.last_exec_us > timing.control_peak_us) {
            timing.control_peak_us = taskStats.last_exec_us;
        }
    }

    // Rate-limited telemetry
    if (ctx_.telemetryScheduler && ctx_.telemetryScheduler->tick(now_ms)) {
        uint32_t t0 = getSystemClock().micros();
        if (ctx_.telemetry) {
            ctx_.telemetry->loop(now_ms);
        }
        timing.telemetry_us = getSystemClock().micros() - t0;
    }

    // Sensor sampling (self-registered + legacy)
    if (ctx_.sensorRegistry) {
        ctx_.sensorRegistry->loopAll(now_ms);
    }
    if (ctx_.ultrasonic) {
        ctx_.ultrasonic->loop(now_ms);
    }

    // Host + router + transports
    {
        uint32_t t0 = getSystemClock().micros();
        if (ctx_.host) {
            ctx_.host->loop(now_ms);
        }
        if (ctx_.wifi) {
            ctx_.wifi->loop();
        }
#if HAS_BLE
        if (ctx_.ble) {
            ctx_.ble->loop();
        }
#endif
        timing.host_us = getSystemClock().micros() - t0;
    }

    // Total loop time
    timing.total_us = getSystemClock().micros() - loop_start_us;
    timing.updatePeaks();

    // Track overruns (loop took longer than configured period)
    // Use MaraConfig as single source of truth for safety_hz
    const uint32_t safety_period_us = config::getMaraConfig().rates.safety_hz > 0
        ? 1000000 / config::getMaraConfig().rates.safety_hz
        : 10000;  // Default to 100Hz if not configured
    if (timing.total_us > safety_period_us) {
        timing.overruns++;
    }

    // Yield to scheduler (platform-specific)
#if PLATFORM_HAS_ARDUINO
    yield();
#endif
}

} // namespace mara
