// src/modules/ControlModule.cpp
// Control system module implementation

#include "module/ControlModule.h"
#include "core/EventBus.h"
#include "command/ModeManager.h"
#include "motor/MotionController.h"
#include "core/LoopRates.h"
#include "control/ControlTelemetry.h"
#include "sensor/EncoderManager.h"
#include "sensor/ImuManager.h"
#include "module/TelemetryModule.h"
#include <algorithm>

ControlModule::ControlModule(
    EventBus* bus,
    ModeManager* mode,
    MotionController* motion,
    EncoderManager* encoder,
    ImuManager* imu,
    TelemetryModule* telemetry
)
    : bus_(bus)
    , mode_(mode)
    , motion_(motion)
    , encoder_(encoder)
    , imu_(imu)
    , telemetry_(telemetry)
{
}

void ControlModule::setup() {
    // Intentionally do not restore persisted control graphs here.
    // The first MCU persistence slice is diagnostics/config-mirror only;
    // operational graphs must be re-uploaded explicitly by an operator.

    // Register JSON telemetry providers for control system visibility
    if (telemetry_) {
        // Combined control telemetry (signals + observers + slots)
        telemetry_->registerProvider("control", [this](ArduinoJson::JsonObject node) {
            ControlTelemetry::provideControlJson(node, signals_, kernel_, observers_);
        });

        // Register binary telemetry providers for high-rate streaming
        telemetry_->registerBinProvider(ControlTelemetry::SECTION_SIGNALS,
            [this](std::vector<uint8_t>& out) {
                out.resize(256);
                size_t len = ControlTelemetry::provideSignalsBin(out.data(), out.size(), signals_);
                out.resize(len);
            });

        telemetry_->registerBinProvider(ControlTelemetry::SECTION_OBSERVERS,
            [this](std::vector<uint8_t>& out) {
                out.resize(256);
                size_t len = ControlTelemetry::provideObserversBin(out.data(), out.size(), observers_);
                out.resize(len);
            });

        telemetry_->registerBinProvider(ControlTelemetry::SECTION_SLOTS,
            [this](std::vector<uint8_t>& out) {
                out.resize(128);
                size_t len = ControlTelemetry::provideSlotsBin(out.data(), out.size(), kernel_);
                out.resize(len);
            });
    }
}

void ControlModule::loop(uint32_t now_ms) {
    // Compute dt
    float dt_s = (last_step_ms_ > 0) 
        ? (now_ms - last_step_ms_) / 1000.0f 
        : 0.01f;
    
    // Clamp dt to reasonable range
    dt_s = std::max(0.001f, std::min(0.1f, dt_s));
    
    last_step_ms_ = now_ms;
    
    // Determine state flags
    bool is_armed = false;
    bool is_active = false;
    
    if (mode_) {
        is_armed = mode_->mode() >= MaraMode::ARMED;
        is_active = mode_->mode() == MaraMode::ACTIVE;
    }
    
    // Step observers FIRST (they provide state estimates to controllers)
    observers_.step(now_ms, dt_s, signals_);
    
    // Step controllers
    kernel_.step(now_ms, dt_s, signals_, is_armed, is_active);
}

void ControlModule::handleEvent(const Event& evt) {
    (void)evt;
    // No special event handling needed.
    // The kernel checks is_armed/is_active each step,
    // so ESTOP automatically stops all controllers.
}