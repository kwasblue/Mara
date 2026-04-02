// src/core/Runtime.cpp
// Runtime orchestrator implementation

#include "core/Runtime.h"
#include "setup/SetupControlTask.h"
#include "loop/LoopFunctions.h"
#include "sensor/SensorRegistry.h"
#include "core/Clock.h"
#include <Arduino.h>
#include <ArduinoOTA.h>

namespace mara {

bool Runtime::setup(const RuntimeConfig& config) {
    config_ = config;

    Serial.begin(config_.serial_baud);
    delay(500);
    Serial.println("\n[Runtime] Booting...");

    // Phase 1: Initialize storage components
    if (!initializeStorage()) {
        Serial.println("[Runtime] FATAL: Storage initialization failed");
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
            Serial.println("[Runtime] WARNING: Control task failed, using cooperative scheduling");
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

    Serial.println("[Runtime] Setup complete");
    LoopRates& r = getLoopRates();
    Serial.printf("[Runtime] Loop rates: ctrl=%dHz safety=%dHz telem=%dHz\n",
                  r.ctrl_hz, r.safety_hz, r.telem_hz);

    return true;
}

void Runtime::loop() {
    if (criticalFailure_) {
        delay(100);
        return;
    }

    uint32_t now_ms = getSystemClock().millis();
    runMainLoop(now_ms);
}

bool Runtime::initializeStorage() {
    storage_.initTransports(Serial, config_.serial_baud, config_.tcp_port);
    storage_.initRouter();
    storage_.initCommands();
    storage_.initControl();
    storage_.initHost(config_.device_name);

    ctx_ = storage_.buildContext();
    return true;
}

bool Runtime::runSetupModules() {
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
            Serial.printf("[%s] FAILED: %s\n",
                          mod->name(),
                          errorCodeToString(result.errorCode()));

            if (mod->isCritical()) {
                Serial.printf("[Runtime] FATAL: Critical module '%s' failed\n", mod->name());
                criticalFailure_ = true;

                if (ctx_.dcMotor) ctx_.dcMotor->stopAll();
                return false;
            }
        }
    }

    return true;
}

bool Runtime::startControlTask() {
    ControlTaskConfig taskCfg;
    taskCfg.rate_hz = config_.control_rate_hz;
    taskCfg.stack_size = config_.control_stack_size;
    taskCfg.priority = config_.control_priority;
    taskCfg.core = config_.control_core;

    controlTaskStarted_ = mara::startControlTask(ctx_, taskCfg);
    if (controlTaskStarted_) {
        Serial.println("[Runtime] FreeRTOS control task started");
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

    // OTA
    ArduinoOTA.handle();

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
    if (timing.total_us > config_.safety_period_us()) {
        timing.overruns++;
    }

    yield();  // Non-blocking yield instead of blocking delay
}

} // namespace mara
