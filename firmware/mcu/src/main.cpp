#include <Arduino.h>
#include <ArduinoOTA.h>

// Core infrastructure
#include "core/Result.h"
#include "core/IModule.h"
#include "core/ServiceContext.h"
#include "core/ServiceStorage.h"
#include "core/LoopRates.h"
#include "core/LoopTiming.h"
#include "core/Clock.h"
#include "sensor/SensorRegistry.h"

// Setup modules
#include "setup/SetupModules.h"
#include "setup/SetupControlTask.h"

// Loop functions
#include "loop/LoopFunctions.h"

// Config
#include "config/PinConfig.h"
#include "config/WifiSecrets.h"
#include "config/MaraConfig.h"

// HAL Logger (for debug output abstraction)
#include "core/Debug.h"

// Set to true to use FreeRTOS task for control loop (Core 1, high priority)
// Set to false to use cooperative scheduling in main loop()
static constexpr bool USE_FREERTOS_CONTROL = true;

// -----------------------------------------------------------------------------
// Global Storage and Context
// -----------------------------------------------------------------------------
static mara::ServiceStorage g_storage;
static mara::ServiceContext g_ctx;

// Critical failure flag - if true, loop() does nothing
static bool g_criticalFailure = false;

// For periodic debug printing
static uint32_t g_lastIpPrintMs = 0;

// Setup modules are defined in SetupManifest.cpp
// Use getSetupManifest() and getSetupManifestSize() to access

// -----------------------------------------------------------------------------
// Helper: Update loop schedulers from LoopRates
// -----------------------------------------------------------------------------
static void updateLoopSchedulers() {
    LoopRates& r = getLoopRates();
    if (g_ctx.safetyScheduler) {
        g_ctx.safetyScheduler->setPeriodMs(r.safety_period_ms());
    }
    if (g_ctx.controlScheduler) {
        g_ctx.controlScheduler->setPeriodMs(r.ctrl_period_ms());
    }
    if (g_ctx.telemetryScheduler) {
        g_ctx.telemetryScheduler->setPeriodMs(r.telem_period_ms());
    }
}

// -----------------------------------------------------------------------------
// setup()
// -----------------------------------------------------------------------------
void setup() {
    // Get serial baud rate from config
    auto& maraCfg = config::getMaraConfig();
    const uint32_t serial_baud = maraCfg.network.serial_baud;

    Serial.begin(serial_baud);
    delay(500);

    // Wire HAL to managers first (this initializes the logger)
    g_storage.initHal();

    // Set up debug logger for DBG_* macros
    auto halCtx = g_storage.hal.buildContext();
    mara::setDebugLogger(halCtx.logger);

    // Wire HAL clock to mara::SystemClock for portable timing
    mara::setHalClock(halCtx.clock);

    Serial.printf("\n[MCU] Booting with USB Serial @ %lu baud + WiFi (AP+STA)...\n", serial_baud);

    const auto cfgIssues = maraCfg.validate();
    for (const auto& issue : cfgIssues) {
        Serial.printf("[CONFIG] %s\n", issue.c_str());
    }
    if (maraCfg.sanitize()) {
        Serial.println("[CONFIG] Invalid runtime config detected; sanitized to safe defaults");
    }

    // =========================================================================
    // Phase 1: Initialize storage components that need runtime parameters
    // =========================================================================

    g_storage.initTransports(Serial, serial_baud, 3333,
                              MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_ROBOT_ID);
    g_storage.initRouter();
    g_storage.initCommands();
    g_storage.initControl();
    g_storage.initHost("ESP32-bot");

    // Build context from storage
    g_ctx = g_storage.buildContext();

    // Initialize handlers with dependencies (must be after buildContext)
    g_storage.initHandlers(g_ctx);

    // =========================================================================
    // Phase 2: Run setup modules from manifest
    // =========================================================================
    mara::ISetupModule** manifest = getSetupManifest();
    size_t manifestSize = getSetupManifestSize();

    for (size_t i = 0; i < manifestSize; ++i) {
        mara::ISetupModule* mod = manifest[i];
        if (!mod) continue;

        auto result = mod->setup(g_ctx);
        if (result.isError()) {
            Serial.printf("[%s] FAILED: %s\n",
                          mod->name(),
                          mara::errorCodeToString(result.errorCode()));

            // Halt on critical module failure
            if (mod->isCritical()) {
                Serial.printf("[FATAL] Critical module '%s' failed. System halted.\n", mod->name());
                Serial.println("[FATAL] Motors disabled. Please reset device after fixing issue.");
                g_criticalFailure = true;

                // Attempt to disable any motors that might have been initialized
                if (g_ctx.dcMotor) g_ctx.dcMotor->stopAll();

                // Flash LED rapidly to indicate failure (if LED pin configured)
                // Don't return - let remaining non-critical modules attempt setup for diagnostics
            }
        }
    }

    // If critical failure occurred, don't complete setup
    if (g_criticalFailure) {
        Serial.println("[FATAL] Setup aborted due to critical failure.");
        return;
    }

    // =========================================================================
    // Phase 3: Start FreeRTOS control task (if enabled)
    // =========================================================================
    if (USE_FREERTOS_CONTROL) {
        mara::ControlTaskConfig taskCfg;
        taskCfg.rate_hz = 100;      // 100Hz control loop
        taskCfg.stack_size = 4096;
        taskCfg.priority = 5;       // High priority
        taskCfg.core = 1;           // Core 1 (Core 0 handles WiFi)

        if (mara::startControlTask(g_ctx, taskCfg)) {
            Serial.println("[MCU] FreeRTOS control task started");
        } else {
            Serial.println("[MCU] WARNING: FreeRTOS control task failed to start, using cooperative scheduling");
        }
    }

    // =========================================================================
    // Phase 4: Final wiring
    // =========================================================================
    // Note: Handler wiring (setControlModule) is done in ServiceStorage.initControl()

    // Add control module to host (ControlModule inherits from IModule)
    if (g_ctx.host && g_ctx.control) {
        g_ctx.host->addModule(g_ctx.control);
    }

    // Initialize loop schedulers from LoopRates
    updateLoopSchedulers();

    Serial.println("[MCU] Setup complete. Waiting for host connection...");

    // Print initial rates
    LoopRates& r = getLoopRates();
    Serial.printf("[MCU] Loop rates: ctrl=%dHz safety=%dHz telem=%dHz\n",
                  r.ctrl_hz, r.safety_hz, r.telem_hz);
}

// -----------------------------------------------------------------------------
// loop()
// -----------------------------------------------------------------------------
void loop() {
    // If critical failure occurred during setup, do nothing except feed watchdog
    if (g_criticalFailure) {
        delay(100);
        return;
    }

    uint32_t loop_start_us = mara::getSystemClock().micros();
    uint32_t now_ms = mara::getSystemClock().millis();

    // Get timing reference
    mara::LoopTiming& timing = mara::getLoopTiming();

    // OTA
    ArduinoOTA.handle();

    // Update scheduler periods (in case rates changed via command)
    updateLoopSchedulers();

    // Rate-limited safety loop
    if (g_ctx.safetyScheduler && g_ctx.safetyScheduler->tick(now_ms)) {
        uint32_t t0 = mara::getSystemClock().micros();
        mara::runSafetyLoop(g_ctx, now_ms);
        timing.safety_us = mara::getSystemClock().micros() - t0;
    }

    // Rate-limited control loop (skip if FreeRTOS task is handling it)
    if (!mara::isControlTaskRunning()) {
        if (g_ctx.controlScheduler && g_ctx.controlScheduler->tick(now_ms)) {
            uint32_t t0 = mara::getSystemClock().micros();
            float ctrl_dt = getLoopRates().ctrl_period_ms() / 1000.0f;
            mara::runControlLoop(g_ctx, now_ms, ctrl_dt);
            timing.control_us = mara::getSystemClock().micros() - t0;
        }
    } else {
        // Get timing from FreeRTOS task
        mara::ControlTaskStats taskStats = mara::getControlTaskStats();
        timing.control_us = taskStats.last_exec_us;
        if (taskStats.last_exec_us > timing.control_peak_us) {
            timing.control_peak_us = taskStats.last_exec_us;
        }
    }

    // Rate-limited telemetry
    if (g_ctx.telemetryScheduler && g_ctx.telemetryScheduler->tick(now_ms)) {
        uint32_t t0 = mara::getSystemClock().micros();
        if (g_ctx.telemetry) {
            g_ctx.telemetry->loop(now_ms);
        }
        timing.telemetry_us = mara::getSystemClock().micros() - t0;
    }

    // Sensor sampling (non-critical, handles own rate limiting)
    // Self-registered sensors loop via registry
    if (g_ctx.sensorRegistry) {
        g_ctx.sensorRegistry->loopAll(now_ms);
    }
    // Legacy ultrasonic (until fully migrated)
    if (g_ctx.ultrasonic) {
        g_ctx.ultrasonic->loop(now_ms);
    }

    // Host + router + transports (always run)
    {
        uint32_t t0 = mara::getSystemClock().micros();
        if (g_ctx.host) {
            g_ctx.host->loop(now_ms);
        }
        if (g_ctx.wifi) {
            g_ctx.wifi->loop();
        }
#if HAS_BLE
        if (g_ctx.ble) {
            g_ctx.ble->loop();
        }
#endif
        timing.host_us = mara::getSystemClock().micros() - t0;
    }

    // Total loop time
    timing.total_us = mara::getSystemClock().micros() - loop_start_us;

    // Track peaks and overruns
    timing.updatePeaks();

    // Check for overrun (loop took longer than configured safety period)
    const uint32_t safety_period_us = 1000000 / config::getMaraConfig().rates.safety_hz;
    if (timing.total_us > safety_period_us) {
        timing.overruns++;
    }

    // Yield to FreeRTOS scheduler without blocking
    yield();
}
