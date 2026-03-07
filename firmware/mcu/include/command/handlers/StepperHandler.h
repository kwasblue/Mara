// include/command/handlers/StepperHandler.h
// Handles stepper motor commands

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "motor/StepperManager.h"
#include "motor/MotionController.h"

class StepperHandler : public ICommandHandler {
public:
    StepperHandler(StepperManager& stepper, MotionController& motion)
        : stepper_(stepper), motion_(motion) {}

    const char* name() const override { return "StepperHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::STEPPER_ENABLE:
            case CmdType::STEPPER_MOVE_REL:
            case CmdType::STEPPER_STOP:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::STEPPER_ENABLE:   handleEnable(payload, ctx);  break;
            case CmdType::STEPPER_MOVE_REL: handleMoveRel(payload, ctx); break;
            case CmdType::STEPPER_STOP:     handleStop(payload, ctx);    break;
            default: break;
        }
    }

private:
    StepperManager& stepper_;
    MotionController& motion_;

    // Implemented in StepperHandler.cpp
    void handleEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleMoveRel(JsonVariantConst payload, CommandContext& ctx);
    void handleStop(JsonVariantConst payload, CommandContext& ctx);
};
