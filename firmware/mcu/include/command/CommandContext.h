// include/command/CommandContext.h
// Shared context passed to command handlers

#pragma once

#include <string>
#include <cmath>
#include <ArduinoJson.h>
#include "config/CommandDefs.h"
#include "core/EventBus.h"
#include "core/Event.h"
#include "core/Clock.h"
#include "core/IntentBuffer.h"
#include "core/ErrorCodes.h"
#include "command/ModeManager.h"

/**
 * Context passed to command handlers.
 * Provides access to shared state and helper methods for ACK/error responses.
 */
struct CommandContext {
    // Current command metadata
    uint32_t seq = 0;
    CmdType cmdType = CmdType::UNKNOWN;
    bool wantAck = true;

    // Core dependencies
    EventBus& bus;
    ModeManager& mode;
    mara::IClock* clock = nullptr;      // Time abstraction (optional, falls back to millis())
    mara::IntentBuffer* intents = nullptr;  // Intent buffer for command-to-actuator separation

    // ACK cache for duplicate detection
    static constexpr int kAckCacheSize = 8;
    struct AckCacheEntry {
        bool valid = false;
        uint32_t seq = 0;
        CmdType cmdType = CmdType::UNKNOWN;
        std::string ackJson;
    };
    AckCacheEntry ackCache[kAckCacheSize];
    int ackCacheWrite = 0;

    CommandContext(EventBus& b, ModeManager& m) : bus(b), mode(m) {}
    CommandContext(EventBus& b, ModeManager& m, mara::IClock* clk)
        : bus(b), mode(m), clock(clk) {}

    // -------------------------------------------------------------------------
    // Time Helpers
    // -------------------------------------------------------------------------

    /// Get current time in milliseconds (uses injected clock or falls back to system clock)
    uint32_t now_ms() const {
        if (clock) return clock->millis();
        return mara::getSystemClock().millis();
    }

    // -------------------------------------------------------------------------
    // Response Helpers
    // -------------------------------------------------------------------------

    void sendAck(const char* cmd, bool ok, JsonDocument& resp) {
        if (!wantAck) return;

        resp["src"] = "mcu";
        resp["cmd"] = cmd;
        resp["ok"] = ok;
        resp["seq"] = seq;

        std::string out;
        serializeJson(resp, out);

        storeAck(cmdType, seq, out);
        publishJson(std::move(out));
    }

    void sendError(const char* cmd, const char* error) {
        if (!wantAck) return;

        JsonDocument resp;
        resp["src"] = "mcu";
        resp["cmd"] = cmd;
        resp["ok"] = false;
        resp["error"] = error;
        resp["seq"] = seq;

        std::string out;
        serializeJson(resp, out);
        storeAck(cmdType, seq, out);
        publishJson(std::move(out));
    }

    /// Send error response with structured error code
    void sendError(const char* cmd, ErrorCode code) {
        if (!wantAck) return;

        JsonDocument resp;
        resp["src"] = "mcu";
        resp["cmd"] = cmd;
        resp["ok"] = false;
        resp["error"] = errorCodeToString(code);
        resp["error_code"] = static_cast<uint16_t>(code);
        resp["seq"] = seq;

        std::string out;
        serializeJson(resp, out);
        storeAck(cmdType, seq, out);
        publishJson(std::move(out));
    }

    /// Send ACK response with structured error code (for failed operations)
    void sendAck(const char* cmd, bool ok, JsonDocument& resp, ErrorCode code) {
        if (!wantAck) return;

        resp["src"] = "mcu";
        resp["cmd"] = cmd;
        resp["ok"] = ok;
        resp["seq"] = seq;
        if (!ok) {
            resp["error"] = errorCodeToString(code);
            resp["error_code"] = static_cast<uint16_t>(code);
        }

        std::string out;
        serializeJson(resp, out);

        storeAck(cmdType, seq, out);
        publishJson(std::move(out));
    }

    // -------------------------------------------------------------------------
    // State Guards
    // -------------------------------------------------------------------------

    bool requireIdle(const char* cmdName) {
        if (mode.mode() == MaraMode::IDLE) {
            return true;
        }
        sendError(cmdName, ErrorCode::INVALID_STATE);
        return false;
    }

    bool requireArmed(const char* cmdName) {
        if (mode.canMove()) {
            return true;
        }
        sendError(cmdName, ErrorCode::NOT_ARMED);
        return false;
    }

    // -------------------------------------------------------------------------
    // Input Validation Helpers
    // -------------------------------------------------------------------------

    /// Check if a required field exists in payload
    bool requireField(JsonVariantConst payload, const char* key, const char* cmdName) {
        if (payload[key].isNull()) {
            char err[32];
            snprintf(err, sizeof(err), "missing_%s", key);
            sendError(cmdName, err);
            return false;
        }
        return true;
    }

    /// Extract a float, rejecting NaN/Inf
    bool requireFloat(JsonVariantConst payload, const char* key, float& out, const char* cmdName) {
        if (!requireField(payload, key, cmdName)) return false;

        float val = payload[key].as<float>();
        if (std::isnan(val) || std::isinf(val)) {
            char err[32];
            snprintf(err, sizeof(err), "invalid_%s", key);
            sendError(cmdName, err);
            return false;
        }
        out = val;
        return true;
    }

    /// Extract an integer
    bool requireInt(JsonVariantConst payload, const char* key, int& out, const char* cmdName) {
        if (!requireField(payload, key, cmdName)) return false;
        out = payload[key].as<int>();
        return true;
    }

    /// Extract a uint8_t (common for slot/id)
    bool requireUint8(JsonVariantConst payload, const char* key, uint8_t& out, const char* cmdName) {
        if (!requireField(payload, key, cmdName)) return false;
        int val = payload[key].as<int>();
        if (val < 0 || val > 255) {
            char err[32];
            snprintf(err, sizeof(err), "invalid_%s", key);
            sendError(cmdName, err);
            return false;
        }
        out = static_cast<uint8_t>(val);
        return true;
    }

    /// Validate a slot index is in range [0, maxSlots)
    bool requireSlot(JsonVariantConst payload, uint8_t& slot, uint8_t maxSlots, const char* cmdName) {
        if (!requireUint8(payload, "slot", slot, cmdName)) return false;
        if (slot >= maxSlots) {
            sendError(cmdName, "invalid_slot");
            return false;
        }
        return true;
    }

    /// Validate a float is within range [min, max]
    bool requireInRange(float val, float minVal, float maxVal, const char* field, const char* cmdName) {
        if (val < minVal || val > maxVal) {
            char err[48];
            snprintf(err, sizeof(err), "%s_out_of_range", field);
            sendError(cmdName, err);
            return false;
        }
        return true;
    }

    /// Validate an int is within range [min, max]
    bool requireIntInRange(int val, int minVal, int maxVal, const char* field, const char* cmdName) {
        if (val < minVal || val > maxVal) {
            char err[48];
            snprintf(err, sizeof(err), "%s_out_of_range", field);
            sendError(cmdName, err);
            return false;
        }
        return true;
    }

    // -------------------------------------------------------------------------
    // ACK Cache (for duplicate command detection)
    // -------------------------------------------------------------------------

    bool tryReplayAck(CmdType cmd, uint32_t cmdSeq) {
        if (!wantAck) return false;
        if (cmdSeq == 0) return false;

        for (int i = 0; i < kAckCacheSize; ++i) {
            auto& e = ackCache[i];
            if (e.valid && e.seq == cmdSeq && e.cmdType == cmd) {
                publishJsonCopy(e.ackJson);
                return true;
            }
        }
        return false;
    }

private:
    void storeAck(CmdType cmd, uint32_t cmdSeq, const std::string& ackJson) {
        if (cmdSeq == 0) return;

        auto& e = ackCache[ackCacheWrite];
        e.valid = true;
        e.seq = cmdSeq;
        e.cmdType = cmd;
        e.ackJson = ackJson;
        ackCacheWrite = (ackCacheWrite + 1) % kAckCacheSize;
    }

    void publishJson(std::string&& out) {
        Event evt;
        evt.type = EventType::JSON_MESSAGE_TX;
        evt.payload.json = std::move(out);
        bus.publish(evt);
    }

    void publishJsonCopy(const std::string& out) {
        std::string copy = out;
        publishJson(std::move(copy));
    }
};
