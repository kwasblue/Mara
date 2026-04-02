// include/command/handlers/MotionHandler.h
// Handles motion commands: SET_VEL, STOP
//
// Uses typed command pattern:
//   1. Decode: JSON/binary -> SetVelocityCmd struct
//   2. Execute: operate on typed struct

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "command/TypedCommands.h"
#include "command/CommandDecoders.h"

// Forward declaration
class MotionController;

class MotionHandler : public ICommandHandler {
public:
    MotionHandler() = default;

    void init(mara::ServiceContext& ctx) override;

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
    /// Implemented in MotionHandler.cpp
    void executeSetVelocity(const mara::cmd::SetVelocityCmd& cmd, CommandContext& ctx);

private:
    MotionController* motion_ = nullptr;
};
