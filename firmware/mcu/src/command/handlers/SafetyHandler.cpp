// src/command/handlers/SafetyHandler.cpp
// Implementation of SafetyHandler methods

#include "command/handlers/SafetyHandler.h"
#include "core/Debug.h"
#include "core/ErrorCodes.h"
#include <cstring>

void SafetyHandler::handleHeartbeat(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] HEARTBEAT");
    mode_.onHostHeartbeat(ctx.now_ms());

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    ctx.sendAck("CMD_HEARTBEAT", true, resp);
}

void SafetyHandler::handleArm(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ARM");
    mode_.arm();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    bool ok = (mode_.mode() == MaraMode::ARMED);
    if (ok) {
        ctx.sendAck("CMD_ARM", true, resp);
    } else {
        ctx.sendAck("CMD_ARM", false, resp, ErrorCode::INVALID_TRANSITION);
    }
}

void SafetyHandler::handleDisarm(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] DISARM");
    mode_.disarm();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    bool ok = (mode_.mode() == MaraMode::IDLE);
    if (ok) {
        ctx.sendAck("CMD_DISARM", true, resp);
    } else {
        ctx.sendAck("CMD_DISARM", false, resp, ErrorCode::INVALID_TRANSITION);
    }
}

void SafetyHandler::handleActivate(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ACTIVATE");
    mode_.activate();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    bool ok = (mode_.mode() == MaraMode::ACTIVE);
    if (ok) {
        ctx.sendAck("CMD_ACTIVATE", true, resp);
    } else {
        ctx.sendAck("CMD_ACTIVATE", false, resp, ErrorCode::INVALID_TRANSITION);
    }
}

void SafetyHandler::handleDeactivate(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] DEACTIVATE");
    mode_.deactivate();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    ctx.sendAck("CMD_DEACTIVATE", true, resp);
}

void SafetyHandler::handleEstop(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ESTOP");
    mode_.estop();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    ctx.sendAck("CMD_ESTOP", true, resp);
}

void SafetyHandler::handleClearEstop(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] CLEAR_ESTOP");
    bool cleared = mode_.clearEstop();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    if (cleared) {
        ctx.sendAck("CMD_CLEAR_ESTOP", true, resp);
    } else {
        ctx.sendAck("CMD_CLEAR_ESTOP", false, resp, ErrorCode::CANNOT_CLEAR_ESTOP);
    }
}

void SafetyHandler::handleStop(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] STOP");
    // Note: This doesn't actually stop motors - that's MotionHandler's job
    // This is just a state acknowledgment
    JsonDocument resp;
    ctx.sendAck("CMD_STOP", true, resp);
}

void SafetyHandler::handleSetMode(JsonVariantConst payload, CommandContext& ctx) {
    const char* modeStr = payload["mode"] | "IDLE";
    DBG_PRINTF("[SAFETY] SET_MODE mode=%s\n", modeStr);

    bool ok = true;
    ErrorCode errorCode = ErrorCode::OK;

    if (mode_.isEstopped()) {
        ok = false;
        errorCode = ErrorCode::IN_ESTOP;
    } else if (strcmp(modeStr, "IDLE") == 0) {
        mode_.disarm();
    } else if (strcmp(modeStr, "ARMED") == 0) {
        mode_.arm();
    } else if (strcmp(modeStr, "ACTIVE") == 0) {
        mode_.arm();
        mode_.activate();
    } else {
        ok = false;
        errorCode = ErrorCode::INVALID_PARAMETER;
    }

    JsonDocument resp;
    resp["mode"] = modeStr;
    resp["state"] = maraModeToString(mode_.mode());
    if (ok) {
        ctx.sendAck("CMD_SET_MODE", true, resp);
    } else {
        ctx.sendAck("CMD_SET_MODE", false, resp, errorCode);
    }
}

void SafetyHandler::handleGetState(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] GET_STATE");

    MaraMode current = mode_.mode();
    bool armed = (current == MaraMode::ARMED || current == MaraMode::ACTIVE);
    bool active = (current == MaraMode::ACTIVE);
    bool estop = mode_.isEstopped();

    JsonDocument resp;
    resp["mode"] = maraModeToString(current);
    resp["armed"] = armed;
    resp["active"] = active;
    resp["estop"] = estop;
    ctx.sendAck("CMD_GET_STATE", true, resp);
}
