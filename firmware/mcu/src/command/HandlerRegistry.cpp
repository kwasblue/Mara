// src/command/HandlerRegistry.cpp
// Implementation of HandlerRegistry singleton

#include "command/HandlerRegistry.h"
#include "command/CommandContext.h"
#include "core/Debug.h"
#include <algorithm>

HandlerRegistry& HandlerRegistry::instance() {
    static HandlerRegistry registry;
    return registry;
}

void HandlerRegistry::registerHandler(IStringHandler* handler) {
    if (!handler) return;

    // Check for duplicate registration
    for (auto* h : handlers_) {
        if (h == handler) {
            DBG_PRINTF("[HREG] Handler already registered: %s\n", handler->name());
            return;
        }
    }

    handlers_.push_back(handler);
    DBG_PRINTF("[HREG] Registered string handler: %s (priority=%d)\n",
               handler->name(), handler->priority());
}

void HandlerRegistry::finalize() {
    if (finalized_) {
        DBG_PRINTLN("[HREG] Already finalized");
        return;
    }

    // Sort handlers by priority (lower priority first)
    std::sort(handlers_.begin(), handlers_.end(),
              [](IStringHandler* a, IStringHandler* b) {
                  return a->priority() < b->priority();
              });

    finalized_ = true;
    DBG_PRINTF("[HREG] Finalized with %d string handlers\n", (int)handlers_.size());

    // Debug: list all handlers and their commands
    for (auto* handler : handlers_) {
        DBG_PRINTF("[HREG]   %s (pri=%d): ", handler->name(), handler->priority());
        const char* const* cmds = handler->commands();
        if (cmds) {
            for (int i = 0; cmds[i] != nullptr; ++i) {
                DBG_PRINTF("%s ", cmds[i]);
            }
        }
        DBG_PRINTLN("");
    }
}

IStringHandler* HandlerRegistry::findHandler(const char* cmd) {
    if (!cmd) return nullptr;

    for (auto* handler : handlers_) {
        const char* const* cmds = handler->commands();
        if (!cmds) continue;

        for (int i = 0; cmds[i] != nullptr; ++i) {
            if (strcmp(cmd, cmds[i]) == 0) {
                return handler;
            }
        }
    }
    return nullptr;
}

bool HandlerRegistry::dispatch(const char* cmd, JsonVariantConst payload, CommandContext& ctx) {
    IStringHandler* handler = findHandler(cmd);
    if (handler) {
        // Check capabilities
        if (!capsAvailable(handler)) {
            uint32_t required = handler->requiredCaps();
            uint32_t missing = required & ~availableCaps_;

            // Build error message with first missing capability
            const char* missingCap = "unknown";
            for (uint32_t bit = 1; bit != 0; bit <<= 1) {
                if (missing & bit) {
                    missingCap = capName(bit);
                    break;
                }
            }

            DBG_PRINTF("[HREG] Capability denied for '%s': missing %s\n", cmd, missingCap);
            ctx.sendError("CAPABILITY_UNAVAILABLE", missingCap);
            return true;  // Return true because we handled it (with error)
        }

        DBG_PRINTF("[HREG] Dispatching '%s' to %s\n", cmd, handler->name());
        handler->handle(cmd, payload, ctx);
        return true;
    }
    return false;
}

const char* HandlerRegistry::capName(uint32_t capBit) {
    switch (capBit) {
        case HandlerCap::WIFI:           return "WIFI";
        case HandlerCap::BLE:            return "BLE";
        case HandlerCap::MQTT:           return "MQTT";
        case HandlerCap::DC_MOTOR:       return "DC_MOTOR";
        case HandlerCap::SERVO:          return "SERVO";
        case HandlerCap::STEPPER:        return "STEPPER";
        case HandlerCap::MOTION_CTRL:    return "MOTION_CTRL";
        case HandlerCap::ENCODER:        return "ENCODER";
        case HandlerCap::IMU:            return "IMU";
        case HandlerCap::LIDAR:          return "LIDAR";
        case HandlerCap::ULTRASONIC:     return "ULTRASONIC";
        case HandlerCap::SIGNAL_BUS:     return "SIGNAL_BUS";
        case HandlerCap::CONTROL_KERNEL: return "CONTROL_KERNEL";
        case HandlerCap::OBSERVER:       return "OBSERVER";
        case HandlerCap::TELEMETRY:      return "TELEMETRY";
        case HandlerCap::SAFETY:         return "SAFETY";
        case HandlerCap::AUDIO:          return "AUDIO";
        default:                         return "unknown";
    }
}
