// include/command/ICommandHandler.h
// Interface for domain-specific command handlers

#pragma once

#include <ArduinoJson.h>
#include "config/CommandDefs.h"

// Forward declarations
struct CommandContext;
namespace mara { struct ServiceContext; }

/**
 * Interface for command handlers.
 * Each handler is responsible for a specific domain (motors, sensors, etc.)
 *
 * Self-Registration Pattern:
 * Handlers can use default constructors and receive dependencies via init().
 * This enables self-registration with REGISTER_CMD_HANDLER macro.
 *
 * Example:
 *   class MyHandler : public ICommandHandler {
 *   public:
 *       MyHandler() = default;
 *       void init(mara::ServiceContext& ctx) override {
 *           myDep_ = ctx.myDep;
 *       }
 *       // ... rest of implementation
 *   };
 *   REGISTER_CMD_HANDLER(MyHandler);
 */
class ICommandHandler {
public:
    virtual ~ICommandHandler() = default;

    /**
     * Initialize handler with dependencies from ServiceContext.
     * Called after all handlers are registered, before finalize().
     * Override this to get dependencies instead of constructor injection.
     * @param ctx Service context containing all available dependencies
     */
    virtual void init(mara::ServiceContext& ctx) { (void)ctx; }

    /**
     * Check if this handler can process the given command type.
     */
    virtual bool canHandle(CmdType cmd) const = 0;

    /**
     * Handle the command.
     * @param cmd The command type
     * @param payload JSON payload with command parameters
     * @param ctx Context for sending ACKs/errors and accessing shared state
     */
    virtual void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) = 0;

    /**
     * Optional: Get handler name for debugging.
     */
    virtual const char* name() const { return "UnnamedHandler"; }
};
