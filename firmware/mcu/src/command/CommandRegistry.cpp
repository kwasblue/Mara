// src/command/CommandRegistry.cpp

#include "command/CommandRegistry.h"
#include "command/HandlerRegistry.h"
#include "command/ModeManager.h"
#include "motor/MotionController.h"
#include "module/ControlModule.h"
#include "control/SignalBus.h"
#include <Arduino.h>

CommandRegistry* CommandRegistry::s_instance = nullptr;

CommandRegistry::CommandRegistry(EventBus& bus, ModeManager& mode, MotionController& motion)
    : ctx_(bus, mode)
    , motion_(&motion)
{
    s_instance = this;
}

void CommandRegistry::registerStringHandler(IStringHandler* handler) {
    if (handler) {
        // Use explicit registry if wired, otherwise fall back to singleton
        HandlerRegistry& hr = handlerRegistry_ ? *handlerRegistry_ : HandlerRegistry::instance();
        hr.registerHandler(handler);
        DBG_PRINTF("[REG] Registered string handler: %s\n", handler->name());
    }
}

void CommandRegistry::registerHandler(ICommandHandler* handler) {
    if (handler) {
        handlers_.push_back(handler);
        DBG_PRINTF("[REG] Registered legacy handler: %s\n", handler->name());
    }
}

void CommandRegistry::setup() {
    DBG_PRINTLN("[REG] CommandRegistry::setup() subscribing");
    ctx_.bus.subscribe(&CommandRegistry::handleEventStatic);
    HandlerRegistry& hr = handlerRegistry_ ? *handlerRegistry_ : HandlerRegistry::instance();
    DBG_PRINTF("[REG] Registered %d string handlers, %d legacy handlers\n",
               (int)hr.handlerCount(),
               (int)handlers_.size());
}

void CommandRegistry::handleEventStatic(const Event& evt) {
    if (s_instance) {
        s_instance->handleEvent(evt);
    }
}

void CommandRegistry::handleEvent(const Event& evt) {
    switch (evt.type) {
    case EventType::JSON_MESSAGE_RX:
        ctx_.mode.onHostHeartbeat(ctx_.now_ms());
        onJsonCommand(evt.payload.json);
        break;
    case EventType::BIN_MESSAGE_RX:
        ctx_.mode.onHostHeartbeat(ctx_.now_ms());
        onBinaryCommand(evt.payload.bin);
        break;
    default:
        break;
    }
}

ICommandHandler* CommandRegistry::findHandler(CmdType cmd) {
    for (auto* handler : handlers_) {
        if (handler->canHandle(cmd)) {
            return handler;
        }
    }
    return nullptr;
}

void CommandRegistry::onJsonCommand(const std::string& jsonStr) {
    DBG_PRINT("[REG] raw JSON: ");
    DBG_PRINTLN(jsonStr.c_str());

    JsonMessage msg;
    if (!parseJsonToMessage(jsonStr, msg)) {
        DBG_PRINT("[REG] Failed to parse JSON: ");
        DBG_PRINTLN(jsonStr.c_str());
        return;
    }

    DBG_PRINTF("[REG] kind=%d typeStr=%s cmdType=%d\n",
               (int)msg.kind, msg.typeStr.c_str(), (int)msg.cmdType);

    // If not a command, we're done
    if (msg.kind != MsgKind::CMD) {
        DBG_PRINT("[REG] Ignoring non-command: ");
        DBG_PRINTLN(msg.typeStr.c_str());
        return;
    }

    // Set current context
    ctx_.seq = msg.seq;
    ctx_.cmdType = msg.cmdType;

    // Force ACK for safety-critical commands
    bool forceAck = (msg.cmdType == CmdType::ESTOP ||
                     msg.cmdType == CmdType::ARM ||
                     msg.cmdType == CmdType::DISARM);
    ctx_.wantAck = forceAck ? true : msg.wantAck;

    // Check for duplicate command replay
    if (ctx_.tryReplayAck(msg.cmdType, msg.seq)) {
        return;
    }

    JsonVariantConst payload = msg.payload.as<JsonVariantConst>();

    // Try new string-based registry first (for self-registered handlers)
    HandlerRegistry& hr = handlerRegistry_ ? *handlerRegistry_ : HandlerRegistry::instance();
    if (hr.dispatch(msg.typeStr.c_str(), payload, ctx_)) {
        return;  // Handled by new registry
    }

    // Fall back to legacy enum-based handlers
    ICommandHandler* handler = findHandler(msg.cmdType);
    if (handler) {
        DBG_PRINTF("[REG] Dispatching to %s\n", handler->name());
        handler->handle(msg.cmdType, payload, ctx_);
    } else {
        DBG_PRINTF("[REG] No handler for cmdType: %s\n", msg.typeStr.c_str());
        ctx_.sendError("UNKNOWN_CMD", "unknown_command");
    }
}

void CommandRegistry::onBinaryCommand(const std::vector<uint8_t>& binData) {
    if (binData.empty()) {
        DBG_PRINTLN("[REG] Empty binary command");
        return;
    }

    uint8_t opcode = binData[0];
    const uint8_t* payload = binData.data() + 1;
    size_t payloadLen = binData.size() - 1;

    auto result = BinaryCommands::decode(payload, payloadLen, opcode);
    if (!result.valid) {
        DBG_PRINTF("[REG] Invalid binary command opcode=0x%02X\n", opcode);
        return;
    }

    uint32_t now_ms = ctx_.now_ms();

    switch (result.opcode) {
    case BinaryCommands::Opcode::SET_VEL:
        DBG_PRINTF("[REG BIN] SET_VEL vx=%.3f omega=%.3f\n",
                   result.set_vel.vx, result.set_vel.omega);
        if (motion_) {
            motion_->setVelocity(result.set_vel.vx, result.set_vel.omega);
            ctx_.mode.onMotionCommand(now_ms, result.set_vel.vx, result.set_vel.omega);
        }
        break;

    case BinaryCommands::Opcode::SET_SIGNAL:
        if (controlModule_) {
            controlModule_->signals().set(
                result.set_signal.id,
                result.set_signal.value,
                now_ms
            );
        }
        break;

    case BinaryCommands::Opcode::SET_SIGNALS:
        if (controlModule_) {
            uint8_t count = result.set_signals.count;
            for (uint8_t i = 0; i < count; i++) {
                uint16_t id;
                float value;
                BinaryCommands::parseSignal(payload + 1, i, id, value);
                controlModule_->signals().set(id, value, now_ms);
            }
        }
        break;

    case BinaryCommands::Opcode::HEARTBEAT:
        // Already handled by mode.onHostHeartbeat() above
        break;

    case BinaryCommands::Opcode::STOP:
        DBG_PRINTLN("[REG BIN] STOP");
        if (motion_) {
            motion_->stop();
        }
        break;
    }
}
