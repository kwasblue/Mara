// include/command/handlers/SafetyHandler.h
// Handles safety and state machine commands: ARM, DISARM, ESTOP, HEARTBEAT, etc.

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"

// Forward declarations
class ModeManager;
class MotionController;
namespace mara {
    class SignatureVerifier;
    class SessionManager;
}

class SafetyHandler : public ICommandHandler {
public:
    SafetyHandler() = default;

    void init(mara::ServiceContext& ctx) override;

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
            case CmdType::SET_MODE:
            case CmdType::GET_STATE:
            case CmdType::SET_SAFETY_TIMEOUTS:
            case CmdType::GET_SAFETY_TIMEOUTS:
            case CmdType::SET_SIGNING_KEY:
            case CmdType::RELEASE_SESSION:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        // State transitions require signature verification when a key is configured
        if (isStateTransition(cmd)) {
            if (!verifySignature(payload, ctx, cmdTypeToString(cmd))) {
                return;  // Error already sent by verifySignature
            }
        }

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
            case CmdType::GET_STATE:    handleGetState(ctx);          break;
            case CmdType::SET_SAFETY_TIMEOUTS: handleSetSafetyTimeouts(payload, ctx); break;
            case CmdType::GET_SAFETY_TIMEOUTS: handleGetSafetyTimeouts(ctx); break;
            case CmdType::SET_SIGNING_KEY: handleSetSigningKey(payload, ctx); break;
            case CmdType::RELEASE_SESSION: handleReleaseSession(payload, ctx); break;
            default: break;
        }
    }

private:
    ModeManager* mode_ = nullptr;
    MotionController* motion_ = nullptr;
    mara::SignatureVerifier* verifier_ = nullptr;
    mara::SessionManager* session_ = nullptr;

    // Check if a command is a state transition that requires signature
    static bool isStateTransition(CmdType cmd);

    // Verify signature for state transition commands
    // Returns true if signature valid or no key configured
    bool verifySignature(JsonVariantConst payload, CommandContext& ctx, const char* cmdName);

    // Implemented in SafetyHandler.cpp
    void handleHeartbeat(CommandContext& ctx);
    void handleArm(CommandContext& ctx);
    void handleDisarm(CommandContext& ctx);
    void handleActivate(CommandContext& ctx);
    void handleDeactivate(CommandContext& ctx);
    void handleEstop(CommandContext& ctx);
    void handleClearEstop(CommandContext& ctx);
    void handleStop(CommandContext& ctx);
    void handleSetMode(JsonVariantConst payload, CommandContext& ctx);
    void handleGetState(CommandContext& ctx);
    void handleSetSafetyTimeouts(JsonVariantConst payload, CommandContext& ctx);
    void handleGetSafetyTimeouts(CommandContext& ctx);
    void handleSetSigningKey(JsonVariantConst payload, CommandContext& ctx);
    void handleReleaseSession(JsonVariantConst payload, CommandContext& ctx);
};
