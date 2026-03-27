// include/modules/ControlModule.h
// Control system module - manages signal bus, observers, and control kernel

#pragma once

#include "core/IModule.h"
#include "core/RealTimeContract.h"
#include "control/SignalBus.h"
#include "control/ControlKernel.h"
#include "control/Observer.h"
#include "control/ControlGraphRuntime.h"

class EventBus;
class ModeManager;
class MotionController;
class EncoderManager;
class ImuManager;
class TelemetryModule;

class ControlModule : public IModule {
public:
    ControlModule(
        EventBus* bus,
        ModeManager* mode,
        MotionController* motion,
        EncoderManager* encoder,
        ImuManager* imu,
        TelemetryModule* telemetry
    );

    RT_UNSAFE void setup() override;
    RT_SAFE void loop(uint32_t now_ms) override;
    RT_SAFE const char* name() const override { return "ControlModule"; }

    void handleEvent(const Event& evt);

    SignalBus& signals() { return signals_; }
    ControlKernel& kernel() { return kernel_; }
    ObserverManager& observers() { return observers_; }
    ControlGraphRuntime& graph() { return graph_; }

    const SignalBus& signals() const { return signals_; }
    const ControlKernel& kernel() const { return kernel_; }
    const ObserverManager& observers() const { return observers_; }
    const ControlGraphRuntime& graph() const { return graph_; }

private:
    EventBus* bus_;
    ModeManager* mode_;
    MotionController* motion_;
    EncoderManager* encoder_;
    ImuManager* imu_;
    TelemetryModule* telemetry_;

    SignalBus signals_;
    ControlKernel kernel_;
    ObserverManager observers_;
    ControlGraphRuntime graph_;

    uint32_t last_step_ms_ = 0;
};
