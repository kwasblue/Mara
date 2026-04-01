// AUTO-GENERATED from ActuatorDef("stepper")
// Implement init() and apply() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_STEPPER

#include "actuator/IActuator.h"
#include <ArduinoJson.h>

namespace mara {

class StepperActuator : public IActuator {
public:

    // Auto-generated from telemetry fields
    struct State {
        int8_t motor_id = 0;
        uint8_t attached = 0;
        uint8_t enabled = 0;
        uint8_t moving = 0;
        uint8_t dir_forward = 0;
        int32_t last_cmd_steps = 0;
        int16_t speed_centi = 0;
    };

    const char* name() const override { return "stepper"; }

    void init() override {
        // TODO: Initialize hardware (PWM, GPIO, etc.)
        attached_ = true;
    }

    void apply(const JsonObject& cmd) override {
        // TODO: Apply command to hardware
        // Commands available: CMD_STEPPER_ENABLE, CMD_STEPPER_MOVE_REL, CMD_STEPPER_MOVE_DEG, CMD_STEPPER_MOVE_REV, CMD_STEPPER_STOP, CMD_STEPPER_GET_POSITION, CMD_STEPPER_RESET_POSITION
    }

    void stop() override {
        // TODO: Emergency stop
    }

    void toJson(JsonObject& out) const override {
        out["motor_id"] = state_.motor_id;
        out["attached"] = state_.attached;
        out["enabled"] = state_.enabled;
        out["moving"] = state_.moving;
        out["dir_forward"] = state_.dir_forward;
        out["last_cmd_steps"] = state_.last_cmd_steps;
        out["speed_centi"] = state_.speed_centi;
    }

        const State& state() const { return state_; }

private:
    bool attached_ = false;
    State state_;
};

} // namespace mara

#endif // HAS_STEPPER
