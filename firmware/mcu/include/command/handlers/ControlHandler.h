// include/command/handlers/ControlHandler.h
// Handles control kernel commands: signals, slots, and graph config storage.

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"

// Forward declarations
class ControlModule;
class ImuManager;
class EncoderManager;

class ControlHandler : public ICommandHandler {
public:
    ControlHandler() = default;

    void init(mara::ServiceContext& ctx) override;

    void setControlModule(ControlModule* cm) { controlModule_ = cm; }

    const char* name() const override { return "ControlHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::CTRL_SIGNAL_DEFINE:
            case CmdType::CTRL_SIGNAL_SET:
            case CmdType::CTRL_SIGNAL_GET:
            case CmdType::CTRL_SIGNALS_LIST:
            case CmdType::CTRL_SIGNAL_DELETE:
            case CmdType::CTRL_SIGNALS_CLEAR:
            case CmdType::CTRL_SIGNAL_TRACE:
            case CmdType::CTRL_AUTO_SIGNALS_CONFIG:
            case CmdType::CTRL_SLOT_CONFIG:
            case CmdType::CTRL_SLOT_ENABLE:
            case CmdType::CTRL_SLOT_RESET:
            case CmdType::CTRL_SLOT_SET_PARAM:
            case CmdType::CTRL_SLOT_SET_PARAM_ARRAY:
            case CmdType::CTRL_SLOT_GET_PARAM:
            case CmdType::CTRL_SLOT_STATUS:
            case CmdType::CTRL_GRAPH_UPLOAD:
            case CmdType::CTRL_GRAPH_CLEAR:
            case CmdType::CTRL_GRAPH_ENABLE:
            case CmdType::CTRL_GRAPH_STATUS:
            case CmdType::CTRL_GRAPH_DEBUG:
            case CmdType::CTRL_GRAPH_COMMIT:
            case CmdType::MCU_DIAGNOSTICS_QUERY:
            case CmdType::MCU_DIAGNOSTICS_RESET:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::CTRL_SIGNAL_DEFINE:         handleSignalDefine(payload, ctx); break;
            case CmdType::CTRL_SIGNAL_SET:            handleSignalSet(payload, ctx); break;
            case CmdType::CTRL_SIGNAL_GET:            handleSignalGet(payload, ctx); break;
            case CmdType::CTRL_SIGNALS_LIST:          handleSignalsList(ctx); break;
            case CmdType::CTRL_SIGNAL_DELETE:         handleSignalDelete(payload, ctx); break;
            case CmdType::CTRL_SIGNALS_CLEAR:         handleSignalsClear(ctx); break;
            case CmdType::CTRL_SIGNAL_TRACE:          handleSignalTrace(payload, ctx); break;
            case CmdType::CTRL_AUTO_SIGNALS_CONFIG:   handleAutoSignalsConfig(payload, ctx); break;
            case CmdType::CTRL_SLOT_CONFIG:           handleSlotConfig(payload, ctx); break;
            case CmdType::CTRL_SLOT_ENABLE:           handleSlotEnable(payload, ctx); break;
            case CmdType::CTRL_SLOT_RESET:            handleSlotReset(payload, ctx); break;
            case CmdType::CTRL_SLOT_SET_PARAM:        handleSlotSetParam(payload, ctx); break;
            case CmdType::CTRL_SLOT_SET_PARAM_ARRAY:  handleSlotSetParamArray(payload, ctx); break;
            case CmdType::CTRL_SLOT_GET_PARAM:        handleSlotGetParam(payload, ctx); break;
            case CmdType::CTRL_SLOT_STATUS:           handleSlotStatus(payload, ctx); break;
            case CmdType::CTRL_GRAPH_UPLOAD:          handleGraphUpload(payload, ctx); break;
            case CmdType::CTRL_GRAPH_CLEAR:           handleGraphClear(ctx); break;
            case CmdType::CTRL_GRAPH_ENABLE:          handleGraphEnable(payload, ctx); break;
            case CmdType::CTRL_GRAPH_STATUS:          handleGraphStatus(ctx); break;
            case CmdType::CTRL_GRAPH_DEBUG:           handleGraphDebug(payload, ctx); break;
            case CmdType::CTRL_GRAPH_COMMIT:          handleGraphCommit(payload, ctx); break;
            case CmdType::MCU_DIAGNOSTICS_QUERY:      handleMcuDiagnosticsQuery(ctx); break;
            case CmdType::MCU_DIAGNOSTICS_RESET:      handleMcuDiagnosticsReset(ctx); break;
            default:
                break;
        }
    }

private:
    ControlModule* controlModule_ = nullptr;
    ImuManager* imu_ = nullptr;
    EncoderManager* encoder_ = nullptr;

    void handleSignalDefine(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalSet(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalGet(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalsList(CommandContext& ctx);
    void handleSignalDelete(JsonVariantConst payload, CommandContext& ctx);
    void handleSignalsClear(CommandContext& ctx);
    void handleSignalTrace(JsonVariantConst payload, CommandContext& ctx);
    void handleAutoSignalsConfig(JsonVariantConst payload, CommandContext& ctx);

    void handleSlotConfig(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotReset(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotSetParam(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotSetParamArray(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotGetParam(JsonVariantConst payload, CommandContext& ctx);
    void handleSlotStatus(JsonVariantConst payload, CommandContext& ctx);

    void handleGraphUpload(JsonVariantConst payload, CommandContext& ctx);
    void handleGraphClear(CommandContext& ctx);
    void handleGraphEnable(JsonVariantConst payload, CommandContext& ctx);
    void handleGraphStatus(CommandContext& ctx);
    void handleGraphDebug(JsonVariantConst payload, CommandContext& ctx);
    void handleGraphCommit(JsonVariantConst payload, CommandContext& ctx);
    void handleMcuDiagnosticsQuery(CommandContext& ctx);
    void handleMcuDiagnosticsReset(CommandContext& ctx);
};
