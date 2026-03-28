// src/command/HandlerRegistry.cpp
// Implementation of HandlerRegistry singleton

#include "command/HandlerRegistry.h"
#include "command/CommandContext.h"
#include "core/Debug.h"
#include <algorithm>

namespace {
constexpr uint32_t FNV1A_OFFSET = 2166136261u;
constexpr uint32_t FNV1A_PRIME  = 16777619u;
}

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

uint32_t HandlerRegistry::hashCommand(const char* cmd) {
    uint32_t hash = FNV1A_OFFSET;
    if (!cmd) return hash;

    while (*cmd) {
        hash ^= static_cast<uint8_t>(*cmd++);
        hash *= FNV1A_PRIME;
    }
    return hash;
}

bool HandlerRegistry::insertIndexEntry(const char* cmd, IStringHandler* handler) {
    if (!cmd || !handler) return false;

    const uint32_t hash = hashCommand(cmd);
    for (size_t probe = 0; probe < INDEX_SIZE; ++probe) {
        const size_t slot = (hash + probe) % INDEX_SIZE;
        if (!index_[slot].cmd) {
            index_[slot].cmd = cmd;
            index_[slot].handler = handler;
            indexOrder_[slot] = static_cast<uint16_t>(indexedCommandCount_++);
            return true;
        }

        if (strcmp(index_[slot].cmd, cmd) == 0) {
            const uint16_t existingOrder = indexOrder_[slot];
            const int existingPriority = index_[slot].handler ? index_[slot].handler->priority() : 1000;
            const int newPriority = handler->priority();

            if (newPriority < existingPriority ||
                (newPriority == existingPriority && indexedCommandCount_ < existingOrder)) {
                index_[slot].handler = handler;
                indexOrder_[slot] = static_cast<uint16_t>(indexedCommandCount_);
            }
            ++indexedCommandCount_;
            return true;
        }
    }

    DBG_PRINTF("[HREG] Command index full, cannot index '%s'\n", cmd);
    return false;
}

void HandlerRegistry::rebuildIndex() {
    for (size_t i = 0; i < INDEX_SIZE; ++i) {
        index_[i] = {};
        indexOrder_[i] = INDEX_EMPTY;
    }
    indexedCommandCount_ = 0;

    for (auto* handler : handlers_) {
        const char* const* cmds = handler ? handler->commands() : nullptr;
        if (!cmds) continue;

        for (int i = 0; cmds[i] != nullptr; ++i) {
            insertIndexEntry(cmds[i], handler);
        }
    }
}

void HandlerRegistry::finalize() {
    // Sort handlers by priority (lower priority first)
    std::sort(handlers_.begin(), handlers_.end(),
              [](IStringHandler* a, IStringHandler* b) {
                  return a->priority() < b->priority();
              });

    rebuildIndex();
    finalized_ = true;
    DBG_PRINTF("[HREG] Finalized with %d string handlers, %u indexed commands\n",
               (int)handlers_.size(), (unsigned)indexedCommandCount_);

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

    if (finalized_ && indexedCommandCount_ > 0) {
        const uint32_t hash = hashCommand(cmd);
        for (size_t probe = 0; probe < INDEX_SIZE; ++probe) {
            const size_t slot = (hash + probe) % INDEX_SIZE;
            if (!index_[slot].cmd) {
                return nullptr;
            }
            if (strcmp(cmd, index_[slot].cmd) == 0) {
                return index_[slot].handler;
            }
        }
        return nullptr;
    }

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
