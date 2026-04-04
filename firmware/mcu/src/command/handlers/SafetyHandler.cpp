// src/command/handlers/SafetyHandler.cpp
// Implementation of SafetyHandler methods

#include "command/handlers/SafetyHandler.h"
#include "command/ModeManager.h"
#include "motor/MotionController.h"
#include "core/ServiceContext.h"
#include "core/Debug.h"
#include "core/ErrorCodes.h"
#include "core/SessionManager.h"
#include "security/SignatureVerifier.h"
#include <cstring>
#include <string>

void SafetyHandler::init(mara::ServiceContext& ctx) {
    mode_ = ctx.mode;
    motion_ = ctx.motion;
    verifier_ = ctx.verifier;
    session_ = ctx.session;
}

bool SafetyHandler::isStateTransition(CmdType cmd) {
    switch (cmd) {
        case CmdType::ARM:
        case CmdType::ACTIVATE:
        case CmdType::DEACTIVATE:
        case CmdType::DISARM:
        case CmdType::ESTOP:
        case CmdType::CLEAR_ESTOP:
            return true;
        default:
            return false;
    }
}

bool SafetyHandler::verifySignature(JsonVariantConst payload, CommandContext& ctx, const char* cmdName) {
    // No verifier or no key configured - allow all commands
    if (!verifier_ || !verifier_->hasKey()) {
        return true;
    }

    // Extract signature from payload
    const char* sig = payload["signature"] | nullptr;
    if (!sig || strlen(sig) == 0) {
        ctx.sendError(cmdName, ErrorCode::UNAUTHORIZED);
        return false;
    }

    // Serialize payload without signature for verification
    // We need to compute signature over the canonical form (sorted keys, no signature field)
    JsonDocument doc;
    for (JsonPairConst kv : payload.as<JsonObjectConst>()) {
        if (strcmp(kv.key().c_str(), "signature") != 0) {
            doc[kv.key()] = kv.value();
        }
    }

    std::string canonical;
    serializeJson(doc, canonical);

    if (!verifier_->verify(canonical.c_str(), canonical.size(), sig)) {
        DBG_PRINTF("[SAFETY] Signature verification failed for %s\n", cmdName);
        ctx.sendError(cmdName, ErrorCode::UNAUTHORIZED);
        return false;
    }

    return true;
}

void SafetyHandler::handleHeartbeat(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] HEARTBEAT");
    mode_->onHostHeartbeat(ctx.now_ms());

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    ctx.sendAck("CMD_HEARTBEAT", true, resp);
}

void SafetyHandler::handleArm(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ARM");
    mode_->arm();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    bool ok = (mode_->mode() == MaraMode::ARMED);
    if (ok) {
        ctx.sendAck("CMD_ARM", true, resp);
    } else {
        ctx.sendAck("CMD_ARM", false, resp, ErrorCode::INVALID_TRANSITION);
    }
}

void SafetyHandler::handleDisarm(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] DISARM");
    mode_->disarm();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    bool ok = (mode_->mode() == MaraMode::IDLE);
    if (ok) {
        ctx.sendAck("CMD_DISARM", true, resp);
    } else {
        ctx.sendAck("CMD_DISARM", false, resp, ErrorCode::INVALID_TRANSITION);
    }
}

void SafetyHandler::handleActivate(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ACTIVATE");
    mode_->activate(ctx.now_ms());

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    bool ok = (mode_->mode() == MaraMode::ACTIVE);
    if (ok) {
        ctx.sendAck("CMD_ACTIVATE", true, resp);
    } else {
        ctx.sendAck("CMD_ACTIVATE", false, resp, ErrorCode::INVALID_TRANSITION);
    }
}

void SafetyHandler::handleDeactivate(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] DEACTIVATE");
    mode_->deactivate(ctx.now_ms());

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    ctx.sendAck("CMD_DEACTIVATE", true, resp);
}

void SafetyHandler::handleEstop(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] ESTOP");
    mode_->estop();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    ctx.sendAck("CMD_ESTOP", true, resp);
}

void SafetyHandler::handleClearEstop(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] CLEAR_ESTOP");
    bool cleared = mode_->clearEstop();

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    if (cleared) {
        ctx.sendAck("CMD_CLEAR_ESTOP", true, resp);
    } else {
        ctx.sendAck("CMD_CLEAR_ESTOP", false, resp, ErrorCode::CANNOT_CLEAR_ESTOP);
    }
}

void SafetyHandler::handleStop(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] STOP");

    // Soft stop: zero velocities without changing robot state
    // Prefer intent buffer (HANDLERS → INTENTS architecture), fallback to direct
    if (ctx.intents) {
        ctx.intents->setVelocityIntent(0.0f, 0.0f, ctx.now_ms());
    } else if (motion_) {
        motion_->stop();
    }

    JsonDocument resp;
    resp["state"] = maraModeToString(mode_->mode());
    ctx.sendAck("CMD_STOP", true, resp);
}

void SafetyHandler::handleSetMode(JsonVariantConst payload, CommandContext& ctx) {
    const char* modeStr = payload["mode"] | "IDLE";
    DBG_PRINTF("[SAFETY] SET_MODE mode=%s\n", modeStr);

    bool ok = true;
    ErrorCode errorCode = ErrorCode::OK;

    if (mode_->isEstopped()) {
        ok = false;
        errorCode = ErrorCode::IN_ESTOP;
    } else if (strcmp(modeStr, "IDLE") == 0) {
        mode_->disarm();
    } else if (strcmp(modeStr, "ARMED") == 0) {
        mode_->arm();
    } else if (strcmp(modeStr, "ACTIVE") == 0) {
        mode_->arm();
        mode_->activate(ctx.now_ms());
    } else {
        ok = false;
        errorCode = ErrorCode::INVALID_PARAMETER;
    }

    JsonDocument resp;
    resp["mode"] = modeStr;
    resp["state"] = maraModeToString(mode_->mode());
    if (ok) {
        ctx.sendAck("CMD_SET_MODE", true, resp);
    } else {
        ctx.sendAck("CMD_SET_MODE", false, resp, errorCode);
    }
}

void SafetyHandler::handleGetState(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] GET_STATE");

    MaraMode current = mode_->mode();
    bool armed = (current == MaraMode::ARMED || current == MaraMode::ACTIVE);
    bool active = (current == MaraMode::ACTIVE);
    bool estop = mode_->isEstopped();

    JsonDocument resp;
    resp["mode"] = maraModeToString(current);
    resp["armed"] = armed;
    resp["active"] = active;
    resp["estop"] = estop;
    ctx.sendAck("CMD_GET_STATE", true, resp);
}

void SafetyHandler::handleSetSafetyTimeouts(JsonVariantConst payload, CommandContext& ctx) {
    uint32_t host_ms = payload["host_timeout_ms"] | 0;
    uint32_t motion_ms = payload["motion_timeout_ms"] | 0;

    DBG_PRINTF("[SAFETY] SET_SAFETY_TIMEOUTS host=%lu motion=%lu\n",
               (unsigned long)host_ms, (unsigned long)motion_ms);

    mode_->setTimeouts(host_ms, motion_ms);

    JsonDocument resp;
    resp["host_timeout_ms"] = mode_->getHostTimeout();
    resp["motion_timeout_ms"] = mode_->getMotionTimeout();
    resp["enabled"] = mode_->timeoutsEnabled();
    ctx.sendAck("CMD_SET_SAFETY_TIMEOUTS", true, resp);
}

void SafetyHandler::handleGetSafetyTimeouts(CommandContext& ctx) {
    DBG_PRINTLN("[SAFETY] GET_SAFETY_TIMEOUTS");

    JsonDocument resp;
    resp["host_timeout_ms"] = mode_->getHostTimeout();
    resp["motion_timeout_ms"] = mode_->getMotionTimeout();
    resp["enabled"] = mode_->timeoutsEnabled();
    ctx.sendAck("CMD_GET_SAFETY_TIMEOUTS", true, resp);
}

void SafetyHandler::handleSetSigningKey(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_SET_SIGNING_KEY";
    DBG_PRINTLN("[SAFETY] SET_SIGNING_KEY");

    if (!verifier_) {
        ctx.sendError(ACK, "no_verifier");
        return;
    }

    const char* keyHex = payload["key"] | nullptr;
    if (!keyHex || strlen(keyHex) != 64) {
        ctx.sendError(ACK, ErrorCode::INVALID_PARAMETER);
        return;
    }

    // Convert hex to bytes
    uint8_t keyBytes[32];
    for (size_t i = 0; i < 32; ++i) {
        auto hexValue = [](char c) -> int {
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            if (c >= 'A' && c <= 'F') return c - 'A' + 10;
            return -1;
        };
        int hi = hexValue(keyHex[i * 2]);
        int lo = hexValue(keyHex[i * 2 + 1]);
        if (hi < 0 || lo < 0) {
            ctx.sendError(ACK, ErrorCode::INVALID_PARAMETER);
            return;
        }
        keyBytes[i] = static_cast<uint8_t>((hi << 4) | lo);
    }

    // Key rotation: if a key is already set, require signature of new key
    if (verifier_->hasKey()) {
        const char* sig = payload["signature"] | nullptr;
        if (!sig || strlen(sig) != 64) {
            ctx.sendError(ACK, ErrorCode::UNAUTHORIZED);
            return;
        }

        // Verify signature over the new key
        if (!verifier_->verify(keyHex, 64, sig)) {
            DBG_PRINTLN("[SAFETY] Key rotation signature failed");
            ctx.sendError(ACK, ErrorCode::UNAUTHORIZED);
            return;
        }
    }

    // Set the new key
    verifier_->setKey(keyBytes, 32);

    JsonDocument resp;
    resp["key_set"] = true;
    ctx.sendAck(ACK, true, resp);
}

void SafetyHandler::handleReleaseSession(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_RELEASE_SESSION";
    DBG_PRINTLN("[SAFETY] RELEASE_SESSION");

    if (!session_) {
        ctx.sendError(ACK, "no_session_manager");
        return;
    }

    // Optionally verify client_id matches current owner
    uint32_t clientId = payload["client_id"] | 0;
    if (clientId != 0 && !session_->isSessionOwner(clientId)) {
        // Not the owner - can't release
        JsonDocument resp;
        resp["released"] = false;
        resp["error"] = "not_owner";
        ctx.sendAck(ACK, false, resp);
        return;
    }

    session_->releaseSession();

    JsonDocument resp;
    resp["released"] = true;
    ctx.sendAck(ACK, true, resp);
}
