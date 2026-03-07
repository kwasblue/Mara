// src/command/handlers/TelemetryHandler.cpp
// Implementation of TelemetryHandler methods

#include "command/handlers/TelemetryHandler.h"
#include "module/LoggingModule.h"
#include "core/LoopRates.h"
#include "core/Debug.h"

void TelemetryHandler::handleSetInterval(JsonVariantConst payload, CommandContext& ctx) {
    uint32_t interval = payload["interval_ms"] | 0;

    DBG_PRINTF("[TELEM] SET_INTERVAL interval=%lu\n", (unsigned long)interval);
    telemetry_.setInterval(interval);

    JsonDocument resp;
    resp["interval_ms"] = interval;
    ctx.sendAck("CMD_TELEM_SET_INTERVAL", true, resp);
}

void TelemetryHandler::handleGetRates(CommandContext& ctx) {
    LoopRates& r = getLoopRates();

    JsonDocument resp;
    resp["ctrl_hz"] = r.ctrl_hz;
    resp["safety_hz"] = r.safety_hz;
    resp["telem_hz"] = r.telem_hz;
    resp["ctrl_ms"] = r.ctrl_period_ms();
    resp["safety_ms"] = r.safety_period_ms();
    resp["telem_ms"] = r.telem_period_ms();
    ctx.sendAck("CMD_GET_RATES", true, resp);
}

void TelemetryHandler::handleCtrlSetRate(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.requireIdle("CMD_CTRL_SET_RATE")) return;

    if (payload["hz"].isNull()) {
        ctx.sendError("CMD_CTRL_SET_RATE", "missing_hz");
        return;
    }

    uint16_t hz = static_cast<uint16_t>(payload["hz"].as<int>());
    if (hz == 0) {
        ctx.sendError("CMD_CTRL_SET_RATE", "invalid_hz");
        return;
    }

    bool inRange = clampHz(hz, LoopRates::CTRL_HZ_MIN, LoopRates::CTRL_HZ_MAX);
    getLoopRates().ctrl_hz = hz;

    JsonDocument resp;
    resp["applied_hz"] = hz;
    resp["in_range"] = inRange;
    resp["ctrl_ms"] = getLoopRates().ctrl_period_ms();
    ctx.sendAck("CMD_CTRL_SET_RATE", true, resp);
}

void TelemetryHandler::handleSafetySetRate(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.requireIdle("CMD_SAFETY_SET_RATE")) return;

    if (payload["hz"].isNull()) {
        ctx.sendError("CMD_SAFETY_SET_RATE", "missing_hz");
        return;
    }

    uint16_t hz = static_cast<uint16_t>(payload["hz"].as<int>());
    if (hz == 0) {
        ctx.sendError("CMD_SAFETY_SET_RATE", "invalid_hz");
        return;
    }

    bool inRange = clampHz(hz, LoopRates::SAFETY_HZ_MIN, LoopRates::SAFETY_HZ_MAX);
    getLoopRates().safety_hz = hz;

    JsonDocument resp;
    resp["applied_hz"] = hz;
    resp["in_range"] = inRange;
    resp["safety_ms"] = getLoopRates().safety_period_ms();
    ctx.sendAck("CMD_SAFETY_SET_RATE", true, resp);
}

void TelemetryHandler::handleTelemSetRate(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.requireIdle("CMD_TELEM_SET_RATE")) return;

    if (payload["hz"].isNull()) {
        ctx.sendError("CMD_TELEM_SET_RATE", "missing_hz");
        return;
    }

    uint16_t hz = static_cast<uint16_t>(payload["hz"].as<int>());
    if (hz == 0) {
        ctx.sendError("CMD_TELEM_SET_RATE", "invalid_hz");
        return;
    }

    bool inRange = clampHz(hz, LoopRates::TELEM_HZ_MIN, LoopRates::TELEM_HZ_MAX);
    getLoopRates().telem_hz = hz;

    JsonDocument resp;
    resp["applied_hz"] = hz;
    resp["in_range"] = inRange;
    resp["telem_ms"] = getLoopRates().telem_period_ms();
    ctx.sendAck("CMD_TELEM_SET_RATE", true, resp);
}

void TelemetryHandler::handleSetLogLevel(JsonVariantConst payload, CommandContext& ctx) {
    const char* levelStr = payload["level"] | "info";

    DBG_PRINTF("[TELEM] SET_LOG_LEVEL level=%s\n", levelStr);

    if (LoggingModule::instance()) {
        LoggingModule::instance()->setLogLevel(levelStr);
    }

    JsonDocument resp;
    resp["level"] = levelStr;
    ctx.sendAck("CMD_SET_LOG_LEVEL", true, resp);
}
