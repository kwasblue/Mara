// AUTO-GENERATED from ActuatorDef("dc_motor")
// Implement init() and apply() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_DC_MOTOR

#include "actuator/IActuator.h"
#include <ArduinoJson.h>

namespace mara {

class DcMotorActuator : public IActuator {
public:

    // Auto-generated from telemetry fields
    struct State {
        uint8_t attached = 0;
        int16_t speed_centi = 0;
    };

    const char* name() const override { return "dc_motor"; }

    void init() override {
        // TODO: Initialize hardware (PWM, GPIO, etc.)
        attached_ = true;
    }

    void apply(const JsonObject& cmd) override {
        // TODO: Apply command to hardware
        // Commands available: CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_DC_VEL_PID_ENABLE, CMD_DC_SET_VEL_TARGET, CMD_DC_SET_VEL_GAINS
    }

    void stop() override {
        // TODO: Emergency stop
    }

    void toJson(JsonObject& out) const override {
        out["attached"] = state_.attached;
        out["speed_centi"] = state_.speed_centi;
    }

        const State& state() const { return state_; }

private:
    bool attached_ = false;
    State state_;
};

} // namespace mara

#endif // HAS_DC_MOTOR
