// src/command/handlers/SafetyHandler.cpp
// Implementation of SafetyHandler methods

#include "command/handlers/SafetyHandler.h"
#include "core/Debug.h"
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
    if (!ok) {
        resp["error"] = "invalid_transition";
    }
    ctx.sendAck("CMD_ARM", ok, resp);
}

void SafetyHandler::handleDisarm(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] DISARM");
    mode_.disarm();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    bool ok = (mode_.mode() == MaraMode::IDLE);
    if (!ok) {
        resp["error"] = "invalid_transition";
    }
    ctx.sendAck("CMD_DISARM", ok, resp);
}

void SafetyHandler::handleActivate(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ACTIVATE");
    mode_.activate();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_.mode());
    bool ok = (mode_.mode() == MaraMode::ACTIVE);
    if (!ok) {
        resp["error"] = "invalid_transition";
    }
    ctx.sendAck("CMD_ACTIVATE", ok, resp);
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
    if (!cleared) {
        resp["error"] = "cannot_clear";
    }
    ctx.sendAck("CMD_CLEAR_ESTOP", cleared, resp);
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
    const char* error = nullptr;

    if (mode_.isEstopped()) {
        ok = false;
        error = "in_estop";
    } else if (strcmp(modeStr, "IDLE") == 0) {
        mode_.disarm();
    } else if (strcmp(modeStr, "ARMED") == 0) {
        mode_.arm();
    } else if (strcmp(modeStr, "ACTIVE") == 0) {
        mode_.arm();
        mode_.activate();
    } else {
        ok = false;
        error = "unsupported_mode";
    }

    JsonDocument resp;
    resp["mode"] = modeStr;
    resp["state"] = maraModeToString(mode_.mode());
    if (!ok && error) {
        resp["error"] = error;
    }
    ctx.sendAck("CMD_SET_MODE", ok, resp);
}
