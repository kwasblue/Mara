// include/command/CommandRegistry.h
// Central dispatcher that routes commands to registered handlers

#pragma once

#include <vector>
#include <string>
#include <ArduinoJson.h>
#include "command/ICommandHandler.h"
#include "command/IStringHandler.h"
#include "command/CommandContext.h"
#include "command/BinaryCommands.h"
#include "core/Clock.h"
#include "core/IntentBuffer.h"
#include "core/EventBus.h"
#include "core/Event.h"
#include "core/Messages.h"
#include "core/Debug.h"

// Forward declarations
class ModeManager;
class MotionController;
class ControlModule;
class HandlerRegistry;

/**
 * Command Registry - Central dispatcher for all commands.
 *
 * Supports two handler types:
 * 1. IStringHandler (preferred) - String-based dispatch, self-registration via REGISTER_HANDLER
 * 2. ICommandHandler (legacy) - Enum-based dispatch, manual registration
 *
 * For new modules, use registerStringHandler() or REGISTER_HANDLER macro.
 */
class CommandRegistry {
public:
    CommandRegistry(EventBus& bus, ModeManager& mode, MotionController& motion);

    /**
     * Register a string-based command handler (preferred for new modules).
     * Handlers are dispatched via HandlerRegistry with priority ordering.
     * Use this in module init() for self-registration.
     */
    void registerStringHandler(IStringHandler* handler);

    /**
     * Register a legacy command handler (enum-based).
     * Handlers are checked in registration order after string handlers.
     */
    void registerHandler(ICommandHandler* handler);

    /**
     * Setup event subscriptions.
     */
    void setup();

    /**
     * Set optional control module (for binary commands).
     */
    void setControlModule(ControlModule* cm) { controlModule_ = cm; }

    /**
     * Set motion controller reference (for binary commands).
     */
    void setMotionController(MotionController* mc) { motion_ = mc; }

    /**
     * Set clock for time injection.
     */
    void setClock(mara::IClock* clk) { ctx_.clock = clk; }

    /**
     * Set intent buffer for command-to-actuator separation.
     */
    void setIntentBuffer(mara::IntentBuffer* ib) { ctx_.intents = ib; }

    /**
     * Set handler registry for explicit wiring (composition root pattern).
     * If not set, falls back to HandlerRegistry::instance().
     */
    void setHandlerRegistry(HandlerRegistry* hr) { handlerRegistry_ = hr; }

    /**
     * Process incoming JSON command.
     */
    void onJsonCommand(const std::string& jsonStr);

    /**
     * Process incoming binary command.
     */
    void onBinaryCommand(const std::vector<uint8_t>& binData);

    /**
     * Get the command context (for handlers that need it).
     */
    CommandContext& context() { return ctx_; }

private:
    // Event handling
    static void handleEventStatic(const Event& evt);
    void handleEvent(const Event& evt);
    static CommandRegistry* s_instance;

    // Find handler for command type
    ICommandHandler* findHandler(CmdType cmd);

    // Members
    std::vector<ICommandHandler*> handlers_;
    CommandContext ctx_;
    MotionController* motion_ = nullptr;
    ControlModule* controlModule_ = nullptr;
    HandlerRegistry* handlerRegistry_ = nullptr;  // Explicit wiring (composition root)
};
