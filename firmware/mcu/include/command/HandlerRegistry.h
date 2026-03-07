// include/command/HandlerRegistry.h
// Singleton registry for string-based command handlers

#pragma once

#include <vector>
#include <cstring>
#include "command/IStringHandler.h"

// Forward declaration
struct CommandContext;

/**
 * HandlerRegistry - Singleton registry for IStringHandler instances.
 *
 * Provides O(1) command lookup via linear search (< 15 handlers expected).
 * Handlers register via static constructors using REGISTER_HANDLER macro.
 *
 * Lifecycle:
 * 1. Static constructors call registerHandler() before main()
 * 2. initCommands() calls finalize() to sort by priority
 * 3. dispatch() routes commands to appropriate handlers
 *
 * Thread Safety:
 * - Registration happens before main() (single-threaded)
 * - dispatch() is called from a single thread (event loop)
 */
class HandlerRegistry {
public:
    /**
     * Get the singleton instance.
     */
    static HandlerRegistry& instance();

    /**
     * Register a handler. Called by REGISTER_HANDLER macro.
     * @param handler Pointer to static handler instance (lives for program lifetime)
     */
    void registerHandler(IStringHandler* handler);

    /**
     * Finalize registrations. Sorts handlers by priority.
     * Call once after all static registrations, before dispatch.
     */
    void finalize();

    /**
     * Dispatch a command to the appropriate handler.
     * @param cmd Command string (e.g., "CMD_SET_VEL")
     * @param payload JSON payload
     * @param ctx Command context
     * @return true if handled, false if no handler found
     */
    bool dispatch(const char* cmd, JsonVariantConst payload, CommandContext& ctx);

    /**
     * Find handler for a specific command.
     * @param cmd Command string
     * @return Handler pointer or nullptr if not found
     */
    IStringHandler* findHandler(const char* cmd);

    /**
     * Get number of registered handlers.
     */
    size_t handlerCount() const { return handlers_.size(); }

    /**
     * Check if registry has been finalized.
     */
    bool isFinalized() const { return finalized_; }

    /**
     * Set available system capabilities.
     * Call during init with bitmask of available features.
     * Dispatch will reject handlers whose requiredCaps aren't met.
     */
    void setAvailableCaps(uint32_t caps) { availableCaps_ = caps; }

    /**
     * Get available system capabilities.
     */
    uint32_t availableCaps() const { return availableCaps_; }

    /**
     * Check if handler's required capabilities are satisfied.
     * @return true if all required caps are available
     */
    bool capsAvailable(const IStringHandler* handler) const {
        uint32_t required = handler->requiredCaps();
        return (required & availableCaps_) == required;
    }

    /**
     * Get human-readable name for a capability bit.
     * For error messages.
     */
    static const char* capName(uint32_t capBit);

private:
    HandlerRegistry() = default;
    HandlerRegistry(const HandlerRegistry&) = delete;
    HandlerRegistry& operator=(const HandlerRegistry&) = delete;

    std::vector<IStringHandler*> handlers_;
    bool finalized_ = false;
    uint32_t availableCaps_ = 0;
};
