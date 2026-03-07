// include/command/handlers/ServoHandler.h
// Handles servo motor commands

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "motor/ServoManager.h"
#include "motor/MotionController.h"

class ServoHandler : public ICommandHandler {
public:
    ServoHandler(ServoManager& servo, MotionController& motion)
        : servo_(servo), motion_(motion) {}

    const char* name() const override { return "ServoHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::SERVO_ATTACH:
            case CmdType::SERVO_DETACH:
            case CmdType::SERVO_SET_ANGLE:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::SERVO_ATTACH:    handleAttach(payload, ctx);   break;
            case CmdType::SERVO_DETACH:    handleDetach(payload, ctx);   break;
            case CmdType::SERVO_SET_ANGLE: handleSetAngle(payload, ctx); break;
            default: break;
        }
    }

private:
    ServoManager& servo_;
    MotionController& motion_;

    // Implemented in ServoHandler.cpp
    void handleAttach(JsonVariantConst payload, CommandContext& ctx);
    void handleDetach(JsonVariantConst payload, CommandContext& ctx);
    void handleSetAngle(JsonVariantConst payload, CommandContext& ctx);
};
