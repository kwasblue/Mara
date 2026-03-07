// include/command/handlers/ControlHandler.h
// Handles control kernel commands: signals and controller slots

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "module/ControlModule.h"

class ControlHandler : public ICommandHandler {
public:
    ControlHandler() : controlModule_(nullptr) {}

    void setControlModule(ControlModule* cm) { controlModule_ = cm; }

    const char* name() const override { return "ControlHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            // Signal commands
            case CmdType::CTRL_SIGNAL_DEFINE:
            case CmdType::CTRL_SIGNAL_SET:
            case CmdType::CTRL_SIGNAL_GET:
            case CmdType::CTRL_SIGNALS_LIST:
            case CmdType::CTRL_SIGNAL_DELETE:
            case CmdType::CTRL_SIGNALS_CLEAR:
            // Slot commands
            case CmdType::CTRL_SLOT_CONFIG:
            case CmdType::CTRL_SLOT_ENABLE:
            case CmdType::CTRL_SLOT_RESET:
            case CmdType::CTRL_SLOT_SET_PARAM:
            case CmdType::CTRL_SLOT_SET_PARAM_ARRAY:
            case CmdType::CTRL_SLOT_GET_PARAM:
            case CmdType::CTRL_SLOT_STATUS:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            // Signals
            case CmdType::CTRL_SIGNAL_DEFINE:     handleSignalDefine(payload, ctx);     break;
            case CmdType::CTRL_SIGNAL_SET:        handleSignalSet(payload, ctx);        break;
            case CmdType::CTRL_SIGNAL_GET:        handleSignalGet(payload, ctx);        break;
            case CmdType::CTRL_SIGNALS_LIST:      handleSignalsList(ctx);               break;
            case CmdType::CTRL_SIGNAL_DELETE:     handleSignalDelete(payload, ctx);     break;
            case CmdType::CTRL_SIGNALS_CLEAR:     handleSignalsClear(ctx);              break;
            // Slots
            case CmdType::CTRL_SLOT_CONFIG:       handleSlotConfig(payload, ctx);       break;
            case CmdType::CTRL_SLOT_ENABLE:       handleSlotEnable(payload, ctx);       break;
            case CmdType::CTRL_SLOT_RESET:        handleSlotReset(payload, ctx);        break;
            case CmdType::CTRL_SLOT_SET_PARAM:    handleSlotSetParam(payload, ctx);     break;
            case CmdType::CTRL_SLOT_SET_PARAM_ARRAY: handleSlotSetParamArray(payload, ctx); break;
            case CmdType::CTRL_SLOT_GET_PARAM:    handleSlotGetParam(payload, ctx);     break;
            case CmdType::CTRL_SLOT_STATUS:       handleSlotStatus(payload, ctx);       break;
            default: break;
        }
    }

private:
    ControlModule* controlModule_;

    // Signal commands - implemented in ControlHandler.cpp
    void handleSignalDefine(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalSet(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalGet(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalsList(CommandContext& ctx);
    void handleSignalDelete(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalsClear(CommandContext& ctx);

    // Slot commands - implemented in ControlHandler.cpp
    void handleSlotConfig(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotReset(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotSetParam(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotSetParamArray(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotGetParam(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotStatus(JsonVariantConst payload, CommandContext& ctx);
};
