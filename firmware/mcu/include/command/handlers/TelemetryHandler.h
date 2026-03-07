// include/command/handlers/TelemetryHandler.h
// Handles telemetry, loop rates, and logging commands

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "module/TelemetryModule.h"

// Helper to clamp Hz and return whether it was in range
inline bool clampHz(uint16_t& hz, uint16_t min_hz, uint16_t max_hz) {
    if (hz < min_hz) { hz = min_hz; return false; }
    if (hz > max_hz) { hz = max_hz; return false; }
    return true;
}

class TelemetryHandler : public ICommandHandler {
public:
    explicit TelemetryHandler(TelemetryModule& telemetry)
        : telemetry_(telemetry) {}

    const char* name() const override { return "TelemetryHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::TELEM_SET_INTERVAL:
            case CmdType::GET_RATES:
            case CmdType::CTRL_SET_RATE:
            case CmdType::SAFETY_SET_RATE:
            case CmdType::TELEM_SET_RATE:
            case CmdType::SET_LOG_LEVEL:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::TELEM_SET_INTERVAL: handleSetInterval(payload, ctx); break;
            case CmdType::GET_RATES:          handleGetRates(ctx);             break;
            case CmdType::CTRL_SET_RATE:      handleCtrlSetRate(payload, ctx); break;
            case CmdType::SAFETY_SET_RATE:    handleSafetySetRate(payload, ctx); break;
            case CmdType::TELEM_SET_RATE:     handleTelemSetRate(payload, ctx); break;
            case CmdType::SET_LOG_LEVEL:      handleSetLogLevel(payload, ctx); break;
            default: break;
        }
    }

private:
    TelemetryModule& telemetry_;

    // Implemented in TelemetryHandler.cpp
    void handleSetInterval(JsonVariantConst payload, CommandContext& ctx);
    void handleGetRates(CommandContext& ctx);
    void handleCtrlSetRate(JsonVariantConst payload, CommandContext& ctx);
    void handleSafetySetRate(JsonVariantConst payload, CommandContext& ctx);
    void handleTelemSetRate(JsonVariantConst payload, CommandContext& ctx);
    void handleSetLogLevel(JsonVariantConst payload, CommandContext& ctx);
};
