// include/command/handlers/SafetyHandler.h
// Handles safety and state machine commands: ARM, DISARM, ESTOP, HEARTBEAT, etc.

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "command/ModeManager.h"

class SafetyHandler : public ICommandHandler {
public:
    explicit SafetyHandler(ModeManager& mode) : mode_(mode) {}

    const char* name() const override { return "SafetyHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::HEARTBEAT:
            case CmdType::ARM:
            case CmdType::DISARM:
            case CmdType::ACTIVATE:
            case CmdType::DEACTIVATE:
            case CmdType::ESTOP:
            case CmdType::CLEAR_ESTOP:
            case CmdType::STOP:
            case CmdType::SET_MODE:
            case CmdType::GET_STATE:
            case CmdType::SET_SAFETY_TIMEOUTS:
            case CmdType::GET_SAFETY_TIMEOUTS:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::HEARTBEAT:    handleHeartbeat(ctx);         break;
            case CmdType::ARM:          handleArm(ctx);               break;
            case CmdType::DISARM:       handleDisarm(ctx);            break;
            case CmdType::ACTIVATE:     handleActivate(ctx);          break;
            case CmdType::DEACTIVATE:   handleDeactivate(ctx);        break;
            case CmdType::ESTOP:        handleEstop(ctx);             break;
            case CmdType::CLEAR_ESTOP:  handleClearEstop(ctx);        break;
            case CmdType::STOP:         handleStop(ctx);              break;
            case CmdType::SET_MODE:     handleSetMode(payload, ctx);  break;
            case CmdType::GET_STATE:    handleGetState(ctx);          break;
            case CmdType::SET_SAFETY_TIMEOUTS: handleSetSafetyTimeouts(payload, ctx); break;
            case CmdType::GET_SAFETY_TIMEOUTS: handleGetSafetyTimeouts(ctx); break;
            default: break;
        }
    }

private:
    ModeManager& mode_;

    // Implemented in SafetyHandler.cpp
    void handleHeartbeat(CommandContext& ctx);
    void handleArm(CommandContext& ctx);
    void handleDisarm(CommandContext& ctx);
    void handleActivate(CommandContext& ctx);
    void handleDeactivate(CommandContext& ctx);
    void handleEstop(CommandContext& ctx);
    void handleClearEstop(CommandContext& ctx);
    void handleStop(CommandContext& ctx);
    void handleSetMode(JsonVariantConst payload, CommandContext& ctx);
    void handleGetState(CommandContext& ctx);
    void handleSetSafetyTimeouts(JsonVariantConst payload, CommandContext& ctx);
    void handleGetSafetyTimeouts(CommandContext& ctx);
};
