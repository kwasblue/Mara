// include/command/handlers/StepperHandler.h
// Handles stepper motor commands

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"

// Forward declarations
class StepperManager;
class MotionController;

class StepperHandler : public ICommandHandler {
public:
    StepperHandler() = default;

    void init(mara::ServiceContext& ctx) override;

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
    StepperManager* stepper_ = nullptr;
    MotionController* motion_ = nullptr;

    // Implemented in StepperHandler.cpp
    void handleEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleMoveRel(JsonVariantConst payload, CommandContext& ctx);
    void handleStop(JsonVariantConst payload, CommandContext& ctx);
};
