// core/Messages.h
#pragma once
#include <cstdint>
#include <string>
#include <ArduinoJson.h>
#include "config/CommandDefs.h"

enum class MsgType : uint8_t {
    // ---- Low-level transport primitives ----
    PING        = 0x01,
    PONG        = 0x02,
    HEARTBEAT   = 0x03,

    // ---- Identity / boot ----
    WHOAMI      = 0x10,
    HELLO       = 0x11,

    // ---- Telemetry ----
    STATUS      = 0x20,  // robot -> host (snapshot/telemetry)

    // ---- Logging ----
    LOG         = 0x30,  // robot -> host log line

    // ---- Low-level config ----
    SET_PARAM   = 0x40,  // host -> robot (update parameter)
    GET_PARAM   = 0x41,
    PARAM_VALUE = 0x42,

    // ---- NEW: High-level JSON command envelope ----
    CMD_JSON    = 0x50,  // host -> robot (structured HI-LEVEL COMMAND)

    // ---- Errors ----
    ERROR       = 0x7F,
};

// === High-level JSON message classification ===
enum class MsgKind {
    CMD,
    TELEMETRY,
    EVENT,
    RESP,
    ERROR,
    STEPPER_MOVE_REL,
    STEPPER_STOP,
    STEPPER_ENABLE,
    UNKNOWN
};

inline MsgKind msgKindFromString(const std::string& s) {
    if (s == "cmd")        return MsgKind::CMD;
    if (s == "telemetry")  return MsgKind::TELEMETRY;
    if (s == "event")      return MsgKind::EVENT;
    if (s == "resp")       return MsgKind::RESP;
    if (s == "error")      return MsgKind::ERROR;
    return MsgKind::UNKNOWN;
}

// High-level JSON message representation (robot-side view)
struct JsonMessage {
    MsgKind     kind      = MsgKind::UNKNOWN;
    CmdType     cmdType   = CmdType::UNKNOWN;  // from CommandDefs.h
    std::string typeStr;                       // raw "type" field (e.g. "CMD_SET_MODE")
    uint32_t    seq       = 0;
    JsonDocument payload;                      // ArduinoJson v7 document
    bool wantAck = true;
    explicit JsonMessage()
        : payload() {}                         // default-constructed JsonDocument
};

// Parse a JSON string into JsonMessage
inline bool parseJsonToMessage(const std::string& jsonStr, JsonMessage& outMsg) {
    JsonDocument doc;  // ArduinoJson v7: dynamic doc managed internally

    auto err = deserializeJson(doc, jsonStr);
    if (err) {
        // Optionally: Serial.printf("[CMD] JSON parse error: %s\n", err.c_str());
        return false;
    }

    const char* kindStr = doc["kind"] | "unknown";
    const char* typeStr = doc["type"] | "UNKNOWN";

    outMsg.kind    = msgKindFromString(kindStr);
    outMsg.typeStr = typeStr ? typeStr : "UNKNOWN";
    // Check both "ack" and "wantAck" fields, defaulting to true
    outMsg.wantAck = doc["wantAck"] | (doc["ack"] | true);

    // Use generated function from CommandDefs.h
    outMsg.cmdType = (outMsg.kind == MsgKind::CMD)
        ? cmdTypeFromString(outMsg.typeStr)
        : CmdType::UNKNOWN;

    outMsg.seq = doc["seq"] | 0;

    JsonVariant payload = doc["payload"];
    if (!payload.isNull()) {
        // has payload
        outMsg.payload = payload;
    } else {
        outMsg.payload = doc; // fallback
    }

    return true;
}