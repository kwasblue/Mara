// include/command/handlers/SafetyHandler.h
// Handles safety and state machine commands: ARM, DISARM, ESTOP, HEARTBEAT, etc.

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "command/ModeManager.h"
#include "core/Debug.h"

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
            case CmdType::SET_MODE:  // Legacy
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
            default: break;
        }
    }

private:
    ModeManager& mode_;

    void handleHeartbeat(CommandContext& ctx) {
        DBG_PRINTLN("[SAFETY] HEARTBEAT");
        mode_.onHostHeartbeat(ctx.now_ms());

        JsonDocument resp;
        resp["state"] = maraModeToString(mode_.mode());
        ctx.sendAck("CMD_HEARTBEAT", true, resp);
    }

    void handleArm(CommandContext& ctx) {
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

    void handleDisarm(CommandContext& ctx) {
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

    void handleActivate(CommandContext& ctx) {
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

    void handleDeactivate(CommandContext& ctx) {
        DBG_PRINTLN("[SAFETY] DEACTIVATE");
        mode_.deactivate();

        JsonDocument resp;
        resp["state"] = maraModeToString(mode_.mode());
        ctx.sendAck("CMD_DEACTIVATE", true, resp);
    }

    void handleEstop(CommandContext& ctx) {
        DBG_PRINTLN("[SAFETY] ESTOP");
        mode_.estop();

        JsonDocument resp;
        resp["state"] = maraModeToString(mode_.mode());
        ctx.sendAck("CMD_ESTOP", true, resp);
    }

    void handleClearEstop(CommandContext& ctx) {
        DBG_PRINTLN("[SAFETY] CLEAR_ESTOP");
        bool cleared = mode_.clearEstop();

        JsonDocument resp;
        resp["state"] = maraModeToString(mode_.mode());
        if (!cleared) {
            resp["error"] = "cannot_clear";
        }
        ctx.sendAck("CMD_CLEAR_ESTOP", cleared, resp);
    }

    void handleStop(CommandContext& ctx) {
        DBG_PRINTLN("[SAFETY] STOP");
        // Note: This doesn't actually stop motors - that's MotionHandler's job
        // This is just a state acknowledgment
        JsonDocument resp;
        ctx.sendAck("CMD_STOP", true, resp);
    }

    void handleSetMode(JsonVariantConst payload, CommandContext& ctx) {
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
};
