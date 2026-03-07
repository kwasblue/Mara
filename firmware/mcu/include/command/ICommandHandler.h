// include/command/ICommandHandler.h
// Interface for domain-specific command handlers

#pragma once

#include <ArduinoJson.h>
#include "config/CommandDefs.h"

// Forward declaration
struct CommandContext;

/**
 * Interface for command handlers.
 * Each handler is responsible for a specific domain (motors, sensors, etc.)
 */
class ICommandHandler {
public:
    virtual ~ICommandHandler() = default;

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
