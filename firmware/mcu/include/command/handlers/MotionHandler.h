// include/command/handlers/MotionHandler.h
// Handles motion commands: SET_VEL, STOP
//
// Uses typed command pattern:
//   1. Decode: JSON/binary → SetVelocityCmd struct
//   2. Execute: operate on typed struct

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "command/TypedCommands.h"
#include "command/CommandDecoders.h"
#include "motor/MotionController.h"
#include "core/Debug.h"
#include <cmath>

class MotionHandler : public ICommandHandler {
public:
    MotionHandler(MotionController& motion) : motion_(motion) {}

    const char* name() const override { return "MotionHandler"; }

    bool canHandle(CmdType cmd) const override {
        return cmd == CmdType::SET_VEL;
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        if (cmd == CmdType::SET_VEL) {
            // Decode JSON to typed command
            auto result = mara::cmd::decodeSetVelocity(payload);
            if (!result.valid) {
                ctx.sendError("CMD_SET_VEL", result.error);
                return;
            }
            // Execute typed command
            executeSetVelocity(result.cmd, ctx);
        }
    }

    /// Execute a typed SetVelocityCmd (can be called from binary path too)
    void executeSetVelocity(const mara::cmd::SetVelocityCmd& cmd, CommandContext& ctx) {
        const uint32_t now_ms = ctx.now_ms();

        float safe_vx = 0.0f, safe_omega = 0.0f;
        if (!ctx.mode.validateVelocity(cmd.vx, cmd.omega, safe_vx, safe_omega)) {
            DBG_PRINTF("[MOTION] SET_VEL invalid: vx=%f omega=%f\n", cmd.vx, cmd.omega);
            ctx.sendError("CMD_SET_VEL", "invalid_velocity");
            return;
        }

        // Always allow "STOP" even if not armed
        const bool is_stop_cmd = (fabsf(safe_vx) < 1e-6f) && (fabsf(safe_omega) < 1e-6f);
        if (is_stop_cmd) {
            ctx.mode.onMotionCommand(now_ms, 0.0f, 0.0f);
            // Store zero velocity intent (control task will consume and apply)
            if (ctx.intents) {
                ctx.intents->setVelocityIntent(0.0f, 0.0f, now_ms);
            } else {
                motion_.stop();  // Fallback for non-intent path
            }

            JsonDocument resp;
            resp["vx"] = safe_vx;
            resp["omega"] = safe_omega;
            resp["state"] = maraModeToString(ctx.mode.mode());
            ctx.sendAck("CMD_SET_VEL", true, resp);
            return;
        }

        // Gate non-zero motion
        if (!ctx.mode.canMove()) {
            DBG_PRINTF("[MOTION] SET_VEL rejected: mode=%s\n", maraModeToString(ctx.mode.mode()));
            ctx.sendError("CMD_SET_VEL", "not_armed");
            return;
        }

        ctx.mode.onMotionCommand(now_ms, safe_vx, safe_omega);
        // Store velocity intent (control task will consume and apply)
        if (ctx.intents) {
            ctx.intents->setVelocityIntent(safe_vx, safe_omega, now_ms);
        } else {
            motion_.setVelocity(safe_vx, safe_omega);  // Fallback for non-intent path
        }

        JsonDocument resp;
        resp["vx"] = safe_vx;
        resp["omega"] = safe_omega;
        resp["state"] = maraModeToString(ctx.mode.mode());
        ctx.sendAck("CMD_SET_VEL", true, resp);
    }

private:
    MotionController& motion_;
};
