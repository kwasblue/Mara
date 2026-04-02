// include/command/handlers/ObserverHandler.h
// Handles observer commands for state estimation

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"

// Forward declaration
class ControlModule;

class ObserverHandler : public ICommandHandler {
public:
    ObserverHandler() = default;

    void init(mara::ServiceContext& ctx) override;

    void setControlModule(ControlModule* cm) { controlModule_ = cm; }

    const char* name() const override { return "ObserverHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::OBSERVER_CONFIG:
            case CmdType::OBSERVER_ENABLE:
            case CmdType::OBSERVER_RESET:
            case CmdType::OBSERVER_SET_PARAM:
            case CmdType::OBSERVER_SET_PARAM_ARRAY:
            case CmdType::OBSERVER_STATUS:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::OBSERVER_CONFIG:          handleConfig(payload, ctx);        break;
            case CmdType::OBSERVER_ENABLE:          handleEnable(payload, ctx);        break;
            case CmdType::OBSERVER_RESET:           handleReset(payload, ctx);         break;
            case CmdType::OBSERVER_SET_PARAM:       handleSetParam(payload, ctx);      break;
            case CmdType::OBSERVER_SET_PARAM_ARRAY: handleSetParamArray(payload, ctx); break;
            case CmdType::OBSERVER_STATUS:          handleStatus(payload, ctx);        break;
            default: break;
        }
    }

private:
    ControlModule* controlModule_;

    // Implemented in ObserverHandler.cpp
    void handleConfig(JsonVariantConst payload, CommandContext& ctx);
    void handleEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleReset(JsonVariantConst payload, CommandContext& ctx);
    void handleSetParam(JsonVariantConst payload, CommandContext& ctx);
    void handleSetParamArray(JsonVariantConst payload, CommandContext& ctx);
    void handleStatus(JsonVariantConst payload, CommandContext& ctx);
};
