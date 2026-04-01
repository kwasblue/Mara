// AUTO-GENERATED from ActuatorDef("servo")
// Implement init() and apply() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_SERVO

#include "actuator/IActuator.h"
#include <ArduinoJson.h>

namespace mara {

class ServoActuator : public IActuator {
public:

    const char* name() const override { return "servo"; }

    void init() override {
        // TODO: Initialize hardware (PWM, GPIO, etc.)
        attached_ = true;
    }

    void apply(const JsonObject& cmd) override {
        // TODO: Apply command to hardware
        // Commands available: CMD_SERVO_ATTACH, CMD_SERVO_DETACH, CMD_SERVO_SET_ANGLE, CMD_SERVO_SET_PULSE
    }

    void stop() override {
        // TODO: Emergency stop
    }

    

private:
    bool attached_ = false;

};

} // namespace mara

#endif // HAS_SERVO
