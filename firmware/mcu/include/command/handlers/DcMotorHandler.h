// include/command/handlers/DcMotorHandler.h
// Handles DC motor commands including velocity PID

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "motor/DcMotorManager.h"

class DcMotorHandler : public ICommandHandler {
public:
    explicit DcMotorHandler(DcMotorManager& dc) : dc_(dc) {}

    const char* name() const override { return "DcMotorHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::DC_SET_SPEED:
            case CmdType::DC_STOP:
            case CmdType::DC_VEL_PID_ENABLE:
            case CmdType::DC_SET_VEL_TARGET:
            case CmdType::DC_SET_VEL_GAINS:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::DC_SET_SPEED:      handleSetSpeed(payload, ctx);     break;
            case CmdType::DC_STOP:           handleStop(payload, ctx);         break;
            case CmdType::DC_VEL_PID_ENABLE: handleVelPidEnable(payload, ctx); break;
            case CmdType::DC_SET_VEL_TARGET: handleSetVelTarget(payload, ctx); break;
            case CmdType::DC_SET_VEL_GAINS:  handleSetVelGains(payload, ctx);  break;
            default: break;
        }
    }

private:
    DcMotorManager& dc_;

    // Implemented in DcMotorHandler.cpp
    void handleSetSpeed(JsonVariantConst payload, CommandContext& ctx);
    void handleStop(JsonVariantConst payload, CommandContext& ctx);
    void handleVelPidEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleSetVelTarget(JsonVariantConst payload, CommandContext& ctx);
    void handleSetVelGains(JsonVariantConst payload, CommandContext& ctx);
};
